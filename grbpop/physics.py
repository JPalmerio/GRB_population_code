import numpy as np
import time
import logging
import scipy.integrate as integrate
import constants as cst
# from multiprocessing import Pool
# from functools import partial

log = logging.getLogger(__name__)

try:
    import f90_functions as f90f
    f90 = True
except ImportError:
    f90 = False
    log.error("Could not import f90_functions, f90 set to False")


def Eiso(L, z, Cvar, t90obs, Ep, alpha, beta, ktild, Emin, Emax,
    precision=100, f90=True, **extra_args):
    """
        Returns the source frame isotropic equivalent energy in [erg]
        between Emin and Emax.
        L    : erg/s
        t90obs  : s     (observer frame)
        Ep   : keV   (source frame)
        Emin : keV   (SOURCE !!! frame)
        Emax : keV   (SOURCE !!! frame)
    """
    try:
        Nb_GRBs = len(L)
    except TypeError:
        Nb_GRBs = 1

    if Nb_GRBs > 1:
        xmin = Emin/Ep
        xmax = Emax/Ep
        x = np.logspace(np.log10(xmin), np.log10(xmax), precision, axis=-1)
        if f90:
            xBs = xBtild(x, ktild, alpha, beta)
            xB = f90f.f90f.integrate_2d(x=x, y=xBs)
        else:
            xB = np.zeros(Nb_GRBs)
            for i in range(Nb_GRBs):
                xB[i] = integrate.trapz(xBtild(x[i], ktild[i], alpha[i], beta[i]), x[i], axis=0)
        Eiso = xB * L * Cvar * t90obs / (1.+z)  # in cgs (erg)
    else:
        xmin = Emin/Ep
        xmax = Emax/Ep
        x = np.logspace(np.log10(xmin), np.log10(xmax), precision)
        if f90:
            xB = f90f.f90f.integrate_1d(x=x, y=xBtild(x, ktild, alpha, beta))
        else:
            xB = integrate.trapz(xBtild(x, ktild, alpha, beta), x, axis=0)
        Eiso = xB * L * Cvar * t90obs / (1.+z)  # in cgs (erg)

    return Eiso


def Btild(x, ktild, alpha, beta, spec='Band'):
    """
        Unitless spectral shape (of L_E/E, i.e. photon spectrum in ph/cm2/s/keV)
    """

    # Need this for broadcasting in higher dimensions
    if x.ndim == 2:
        alpha = alpha[:, np.newaxis]
        beta = beta[:, np.newaxis]
        ktild = ktild[:, np.newaxis]

    if spec == 'Band':
        x_c = (beta - alpha) / (2.0 - alpha)
        Btild_1 = ktild * x**(-alpha) * np.exp((alpha - 2.0) * x)
        Btild_2 = ktild * x**(-beta) * np.exp(alpha - beta) * x_c**(beta - alpha)
        Btild = np.where((x <= x_c), Btild_1, Btild_2)
    elif spec == 'BPL':
        # ktild = (2.0-alpha) * (beta-2.0) / (beta-alpha)
        Btild_1 = ktild * x**(-alpha)
        Btild_2 = ktild * x**(-beta)
        Btild = np.where((x <= 1.0), Btild_1, Btild_2)
    else:
        raise ValueError

    return Btild


def xBtild(x, ktild, alpha, beta, spec='Band'):
    """
        Unitless spectral shape (of L_E i.e. energy spectrum in erg/cm2/s/keV)
    """

    # Need this for broadcasting in higher dimensions
    if x.ndim == 2:
        alpha = alpha[:, np.newaxis]
        beta = beta[:, np.newaxis]
        ktild = ktild[:, np.newaxis]

    if spec == 'Band':
        x_c = (beta - alpha) / (2.0 - alpha)
        Btild_1 = ktild * x**(1.0-alpha) * np.exp((alpha - 2.0) * x)
        Btild_2 = ktild * x**(1.0-beta) * np.exp(alpha - beta) * x_c**(beta - alpha)
        Btild = np.where((x <= x_c), Btild_1, Btild_2)
    elif spec == 'BPL':
        ktild = (2.0-alpha) * (beta-2.0) / (beta-alpha)
        Btild_1 = ktild * x**(1.0-alpha)
        Btild_2 = ktild * x**(1.0-beta)
        Btild = np.where((x <= 1.0), Btild_1, Btild_2)
    else:
        raise ValueError

    return Btild


def pht_flux(L, z, Ep, D_L, alpha, beta, ktild, Emin, Emax, spec='Band',
    precision=100, f90=True, **extra_args):
    """
        Returns the photon flux in [ph/cm2/s] between Emin and Emax.
        L    : erg/s
        Ep   : keV   (source frame)
        D_L  : Mpc
        Emin : keV   (observer frame)
        Emax : keV   (observer frame)
    """
    try:
        Nb_GRBs = len(L)
    except TypeError:
        Nb_GRBs = 1

    if Nb_GRBs > 1:
        xmin = (1.+z)*Emin/Ep
        xmax = (1.+z)*Emax/Ep
        x = np.logspace(np.log10(xmin), np.log10(xmax), precision, axis=-1)
        if f90:
            Bs = Btild(x, ktild, alpha, beta, spec=spec)
            B = f90f.f90f.integrate_2d(x=x, y=Bs)
        else:
            B = np.zeros(Nb_GRBs)
            for i in range(Nb_GRBs):
                B[i] = integrate.trapz(Btild(x[i], ktild[i], alpha[i], beta[i], spec=spec), x[i], axis=0)
        pht_flux = B * (1.+z) * L/(4.*np.pi*Ep*cst.keV*(D_L*cst.Mpc)**2)  # in cgs (ph/cm2/s)
    else:
        xmin = (1.+z)*Emin/Ep
        xmax = (1.+z)*Emax/Ep
        x = np.logspace(np.log10(xmin), np.log10(xmax), precision)
        if f90:
            B = f90f.f90f.integrate_1d(x=x, y=Btild(x, ktild, alpha, beta, spec=spec))
        else:
            B = integrate.trapz(Btild(x, ktild, alpha, beta, spec=spec), x, axis=0)
        pht_flux = B * (1.+z) * L/(4.*np.pi*Ep*cst.keV*(D_L*cst.Mpc)**2)  # in cgs (ph/cm2/s)

    return pht_flux


def erg_flux(L, z, Ep, D_L, alpha, beta, ktild, Emin, Emax, spec='Band',
    precision=100, f90=True, **extra_args):
    """
        Returns the energy flux in [erg/cm2/s] between Emin and Emax.
        L    : erg/s
        Ep   : keV   (source frame)
        D_L  : Mpc
        Emin : keV   (observer frame)
        Emax : keV   (observer frame)
    """
    try:
        Nb_GRBs = len(L)
    except TypeError:
        Nb_GRBs = 1

    if Nb_GRBs > 1:
        xmin = (1.+z)*Emin/Ep
        xmax = (1.+z)*Emax/Ep
        x = np.logspace(np.log10(xmin), np.log10(xmax), precision, axis=-1)
        if f90:
            xBs = xBtild(x, ktild, alpha, beta, spec=spec)
            xB = f90f.f90f.integrate_2d(x=x, y=xBs)
        else:
            xB = np.zeros(Nb_GRBs)
            for i in range(Nb_GRBs):
                xB[i] = integrate.trapz(xBtild(x[i], ktild[i], alpha[i], beta[i], spec=spec), x[i], axis=0)
        erg_flux = xB * L/(4.*np.pi*(D_L*cst.Mpc)**2)  # in cgs (erg/cm2/s)
    else:
        xmin = (1.+z)*Emin/Ep
        xmax = (1.+z)*Emax/Ep
        x = np.logspace(np.log10(xmin), np.log10(xmax), precision)
        if f90:
            xB = f90f.f90f.integrate_1d(x=x, y=xBtild(x, ktild, alpha, beta, spec=spec))
        else:
            xB = integrate.trapz(xBtild(x, ktild, alpha, beta, spec=spec), x, axis=0)
        erg_flux = xB * L/(4.*np.pi*(D_L*cst.Mpc)**2)  # in cgs (erg/cm2/s)

    return erg_flux


def cts_flux_ECLAIRs(L, z, Ep, D_L, alpha, beta, ktild, Emin, Emax, eff_area_A_tot, eff_area_E_tot,
    spec='Band', precision=100, f90=True, **extra_args):
    """
        Calculate the number of counts per second per square centimeter
        [cts/cm2/s] between Emin and Emax.
        This is like pht_flux but using an effective area to convert from
        photons to counts. If calculating for more than 1 GRB:
        - L, z, Ep, D_L, alpha, beta must be 1D arrays of size Nb_GRBs
        Note: eff_A is a 2D array of shape (Nb_GRBs, precision) where
        precision is the number of points in the GRB spectrum.
        Units are expected as:
        L    : erg/s
        Ep   : keV
        D_L  : Mpc
        Emin : keV
        Emax : keV
    """
    try:
        Nb_GRBs = len(L)
    except TypeError:
        Nb_GRBs = 1

    if Nb_GRBs > 1:
        xmin = (1.+z)*Emin/Ep
        xmax = (1.+z)*Emax/Ep
        x = np.logspace(np.log10(xmin), np.log10(xmax), precision, axis=-1)
        # Need to create 2D (Nb_GRBs, precision) energy grid to find the corresponding effective area
        E_grid = x * Ep[:, np.newaxis]/(1+z[:, np.newaxis])
        eff_A = eff_area_A_tot[eff_area_E_tot.searchsorted(E_grid)]
        if f90:
            Bs = Btild(x, ktild, alpha, beta, spec=spec)
            B = f90f.f90f.integrate_2d_w(x=x, y=Bs, w=eff_A)
        else:
            B = np.zeros(Nb_GRBs)
            for i in range(Nb_GRBs):
                B[i] = integrate.trapz(eff_A[i]*Btild(x[i], ktild[i], alpha[i], beta[i], spec=spec), x[i], axis=0)
        cts_flux_ECLAIRs = B * (1.+z) * L/(4.*np.pi*Ep*cst.keV*(D_L*cst.Mpc)**2)  # in cgs (cts/cm2/s)
    else:
        xmin = (1.+z)*Emin/Ep
        xmax = (1.+z)*Emax/Ep
        x = np.logspace(np.log10(xmin), np.log10(xmax), precision)
        E_grid = x * Ep / (1.+z)
        eff_A = eff_area_A_tot[eff_area_E_tot.searchsorted(E_grid)]
        if f90:
            B = f90f.f90f.integrate_1d(x=x, y=eff_A*Btild(x, ktild, alpha, beta, spec=spec))
        else:
            B = integrate.trapz(eff_A*Btild(x, ktild, alpha, beta, spec=spec), x, axis=0)
        cts_flux_ECLAIRs = B * (1.+z) * L/(4.*np.pi*Ep*cst.keV*(D_L*cst.Mpc)**2)  # in cgs (cts/cm2/s)

    return cts_flux_ECLAIRs


def erg_flux_ECLAIRs(L, z, Ep, D_L, alpha, beta, ktild, Emin, Emax, eff_area_A_tot, eff_area_E_tot,
    spec='Band', precision=100, f90=True, **extra_args):
    """
        Calculate the amount of energy per second per square centimeter
        [erg/cm2/s] between Emin and Emax.
        This is like erg_flux but using an effective area to convert from
        photons to counts. If calculating for more than 1 GRB:
        - L, z, Ep, D_L, alpha, beta must be 1D arrays of size Nb_GRBs
        Note: eff_A is a 2D array of shape (Nb_GRBs, precision) where
        precision is the number of points in the GRB spectrum.
        Units are expected as:
        L    : erg/s
        Ep   : keV   (source frame)
        D_L  : Mpc
        Emin : keV   (observer frame)
        Emax : keV   (observer frame)
    """
    try:
        Nb_GRBs = len(L)
    except TypeError:
        Nb_GRBs = 1

    if Nb_GRBs > 1:
        xmin = (1.+z)*Emin/Ep
        xmax = (1.+z)*Emax/Ep
        x = np.logspace(np.log10(xmin), np.log10(xmax), precision, axis=-1)
        # Need to create 2D (Nb_GRBs, precision) energy grid to find the corresponding effective area
        E_grid = x * Ep[:, np.newaxis]/(1+z[:, np.newaxis])
        eff_A = eff_area_A_tot[eff_area_E_tot.searchsorted(E_grid)]
        if f90:
            xBs = xBtild(x, ktild, alpha, beta, spec=spec)
            xB = f90f.f90f.integrate_2d_w(x=x, y=xBs, w=eff_A)
        else:
            xB = np.zeros(Nb_GRBs)
            for i in range(Nb_GRBs):
                xB[i] = integrate.trapz(xBtild(x[i], ktild[i], alpha[i], beta[i], spec=spec), x[i], axis=0)
        erg_flux_ECLAIRs = xB * L/(4.*np.pi*(D_L*cst.Mpc)**2)  # in cgs (erg/cm2/s)
    else:
        xmin = (1.+z)*Emin/Ep
        xmax = (1.+z)*Emax/Ep
        x = np.logspace(np.log10(xmin), np.log10(xmax), precision)
        E_grid = x * Ep / (1.+z)
        eff_A = eff_area_A_tot[eff_area_E_tot.searchsorted(E_grid)]
        if f90:
            xB = f90f.f90f.integrate_1d(x=x, y=eff_A*xBtild(x, ktild, alpha, beta, spec=spec))
        else:
            xB = integrate.trapz(eff_A*xBtild(x, ktild, alpha, beta, spec=spec), x, axis=0)
        erg_flux_ECLAIRs = xB * L/(4.*np.pi*(D_L*cst.Mpc)**2)  # in cgs (erg/cm2/s)

    return erg_flux_ECLAIRs


def calc_peak_photon_flux(GRB_prop, instruments, shape='Band', ECLAIRs_prop=None, f90=True):
    """
        Calculates peak photon flux in units of ph/cm2/s (assumed to be
        over a 1s time interval)
    """

    log.info(f"Starting calculations of peak photon fluxes...")

    for name, properties in instruments.items():
        Emin = properties['Emin']
        Emax = properties['Emax']
        log.debug(f"For {name} instrument [{Emin}, {Emax} keV]:")
        t1 = time.time()
        if name == 'ECLAIRs':
            if ECLAIRs_prop is None:
                raise ValueError('If you wish to calculate counts for ECLAIRs you must provide the'
                                 ' ECLAIRs_prop dictionary with the relevent information')
            GRB_prop['_'.join(['pht_cts', name])] = cts_flux_ECLAIRs(**GRB_prop,
                                                                     spec=shape,
                                                                     Emin=ECLAIRs_prop['Emin'],
                                                                     Emax=ECLAIRs_prop['Emax'],
                                                                     eff_area_A_tot=ECLAIRs_prop['eff_area_A'],
                                                                     eff_area_E_tot=ECLAIRs_prop['eff_area_E'],
                                                                     f90=f90)
        else:
            GRB_prop['_'.join(['pht_pflx', name])] = pht_flux(**GRB_prop,
                                                              Emin=Emin,
                                                              Emax=Emax,
                                                              spec=shape,
                                                              f90=f90)
        t2 = time.time()
        log.debug(f"Done in {t2-t1:.3f} s")

    return


def calc_peak_energy_flux(GRB_prop, instruments, shape='Band', ECLAIRs_prop=None, f90=True):
    """
        Calculates peak energy flux in units of erg/cm2/s (assumed to be
        over a 1s time interval)
    """

    log.info(f"Starting calculations of peak energy fluxes...")

    for name, properties in instruments.items():
        Emin = properties['Emin']
        Emax = properties['Emax']
        log.debug(f"For {name} instrument [{Emin}, {Emax} keV]:")
        t1 = time.time()
        if name == 'ECLAIRs':
            if ECLAIRs_prop is None:
                raise ValueError('If you wish to calculate counts for ECLAIRs you must provide the'
                                 ' ECLAIRs_prop dictionary with the relevent information')
            GRB_prop['_'.join(['erg_cts', name])] = erg_flux_ECLAIRs(**GRB_prop,
                                                                     spec=shape,
                                                                     Emin=ECLAIRs_prop['Emin'],
                                                                     Emax=ECLAIRs_prop['Emax'],
                                                                     eff_area_A_tot=ECLAIRs_prop['eff_area_A'],
                                                                     eff_area_E_tot=ECLAIRs_prop['eff_area_E'],
                                                                     f90=f90)
        else:
            GRB_prop['_'.join(['erg_pflx', name])] = erg_flux(**GRB_prop,
                                                              Emin=Emin,
                                                              Emax=Emax,
                                                              spec=shape,
                                                              f90=f90)
        t2 = time.time()
        log.debug(f"Done in {t2-t1:.3f} s")

    return


def calc_photon_fluence(GRB_prop, instruments):
    """
        Calculate the photon fluence in units of ph/cm2 over the T90 of
        the burst.
    """

    log.debug("Starting calculations of photon fluences...")
    t1 = time.time()
    for name in instruments:
        if name == 'ECLAIRs':
            GRB_prop['_'.join(['pht_flnc', name])] = GRB_prop['t90obs']*GRB_prop['Cvar'] * GRB_prop['_'.join(['pht_cts', name])]
        else:
            GRB_prop['_'.join(['pht_flnc', name])] = GRB_prop['t90obs']*GRB_prop['Cvar'] * GRB_prop['_'.join(['pht_pflx', name])]
    t2 = time.time()
    log.debug(f"Done in {t2-t1:.3f} s")

    return


def calc_energy_fluence(GRB_prop, instruments):
    """
        Calculate the energy fluence in units of erg/cm2 over the T90 of
        the burst.
    """

    log.debug(f"Starting calculations of energy fluences...")
    t1 = time.time()
    for name in instruments:
        if name == 'ECLAIRs':
            try:
                GRB_prop['_'.join(['erg_flnc', name])] = GRB_prop['t90obs']*GRB_prop['Cvar'] * GRB_prop['_'.join(['erg_cts', name])]
            except KeyError:
                log.error("The following keys are needed to calculate the energy fluence: 't90obs', 'Cvar', '{}'.\
                           Are you sure you have calculated them?".format('_'.join(['erg_cts', name])))
                raise
        else:
            try:
                GRB_prop['_'.join(['erg_flnc', name])] = GRB_prop['t90obs']*GRB_prop['Cvar'] * GRB_prop['_'.join(['erg_pflx', name])]
            except KeyError:
                log.error("The following keys are needed to calculate the energy fluence: 't90obs', 'Cvar', '{}'.\
                           Are you sure you have calculated them?".format('_'.join(['erg_pflx', name])))
                raise
    t2 = time.time()
    log.debug(f"Done in {t2-t1:.3f} s")

    return


def calc_det_prob_SVOM(cts, offax_corr, omega_ECLAIRs, omega_ECLAIRs_tot, t90obs=1., Cvar=1.,
    n_sigma=6.5, bkg_total=3098.396271499998, f90=True, **extra_args):

    if isinstance(cts, np.ndarray):
        if f90:
            det_prob = f90f.f90f.det_prob_eclairs(cts_ecl=cts, t90obs=t90obs,
                                                  cvar=Cvar,
                                                  offax_corr=offax_corr,
                                                  omega_ecl=omega_ECLAIRs,
                                                  n_sigma=n_sigma,
                                                  threshold=bkg_total)
            det_prob_tot = det_prob[0]
            det_prob_cts = det_prob[1]
            det_prob_flnc = det_prob[2]
        else:
            det_prob_tot = np.zeros(cts.shape)
            det_prob_cts = np.zeros(cts.shape)
            det_prob_flnc = np.zeros(cts.shape)
            flnc = cts * Cvar * t90obs
            cts_thresh = n_sigma * np.sqrt(bkg_total)
            flnc_thresh = n_sigma * np.sqrt(bkg_total/t90obs)
            for i in range(cts.shape[0]):
                _det_prob_cts = np.where((cts[i] * offax_corr >= cts_thresh),
                                         np.ones(offax_corr.shape),
                                         np.zeros(offax_corr.shape))
                _det_prob_flnc = np.where((flnc[i] * offax_corr >= flnc_thresh[i]),
                                          np.ones(offax_corr.shape),
                                          np.zeros(offax_corr.shape))
                _det_prob_tot = (_det_prob_flnc == 1) | (_det_prob_cts == 1)
                det_prob_tot[i] = np.sum(_det_prob_tot*omega_ECLAIRs)/(4*np.pi)
                det_prob_cts[i] = np.sum(_det_prob_cts*omega_ECLAIRs)/(4*np.pi)
                det_prob_flnc[i] = np.sum(_det_prob_flnc*omega_ECLAIRs)/(4*np.pi)
    else:
        if isinstance(t90obs, np.ndarray) or isinstance(Cvar, np.ndarray):
            raise ValueError('If cts is a scalar, t90obs and Cvar must also be scalars and not arrays.')
        flnc = cts * Cvar * t90obs
        cts_thresh = n_sigma * np.sqrt(bkg_total)
        flnc_thresh = n_sigma * np.sqrt(bkg_total * t90obs)
        det_prob_cts = np.where((cts * offax_corr >= cts_thresh),
                                np.ones(offax_corr.shape),
                                np.zeros(offax_corr.shape))
        det_prob_flnc = np.where((flnc * offax_corr >= flnc_thresh),
                                 np.ones(offax_corr.shape),
                                 np.zeros(offax_corr.shape))
        det_prob_tot = np.where((det_prob_cts == 1) | (det_prob_flnc == 1),
                                np.ones(offax_corr.shape),
                                np.zeros(offax_corr.shape))
        det_prob_tot = np.sum(det_prob_tot*omega_ECLAIRs)/(4*np.pi)
        det_prob_cts = np.sum(det_prob_cts*omega_ECLAIRs)/(4*np.pi)
        det_prob_flnc = np.sum(det_prob_flnc*omega_ECLAIRs)/(4*np.pi)
    return det_prob_tot, det_prob_cts, det_prob_flnc


def calc_det_prob(GRB_prop, samples, **ECLAIRs_prop):
    """
        Calculate the detection probability of the GRBs for each sample,
        given the peak flux.
        For ECLAIRs a realistic background threshold is used.

    """

    log.info("Starting calculations of detection probability...")
    Nb_GRBs = len(GRB_prop['z'])

    for name, properties in samples.items():
        instr_name = properties['instrument']

        log.debug(f"{name} sample:")
        t1 = time.time()

        if name == 'ECLAIRs':
            cts = np.asarray(GRB_prop['_'.join(['pht_cts', instr_name])])
            pdet_tot, pdet_cts, pdet_flnc = calc_det_prob_SVOM(cts=cts,
                                                               t90obs=GRB_prop['t90obs'],
                                                               Cvar=GRB_prop['Cvar'],
                                                               **ECLAIRs_prop)
            GRB_prop['_'.join(['pdet', name, 'tot'])] = pdet_tot
            GRB_prop['_'.join(['pdet', name, 'pht_flnc'])] = pdet_flnc
            GRB_prop['_'.join(['pdet', name, 'pht_cts'])] = pdet_cts

        elif name == 'SHOALS':
            erg_flnc = GRB_prop['_'.join(['erg_flnc', instr_name])]
            condition = (erg_flnc >= properties['pflx_min'])
            GRB_prop['_'.join(['pdet', name])] = np.where(condition,
                                                          np.ones(Nb_GRBs),
                                                          np.zeros(Nb_GRBs))
        else:
            pflx = GRB_prop['_'.join(['pht_pflx', instr_name])]
            condition = (pflx >= properties['pflx_min'])

            GRB_prop['_'.join(['pdet', name])] = np.where(condition,
                                                          np.ones(Nb_GRBs),
                                                          np.zeros(Nb_GRBs))
        t2 = time.time()
        log.debug(f"Done in {t2-t1:.3f} s")

    return


# def f_test(a, b, c=0):

#     return a+b+c


# def para_test(a, b, c=0, para=False):

#     try:
#         Nb_GRBs = len(a)
#     except TypeError:
#         Nb_GRBs = 1

#     if para:
#         f = partial(f_test, c=c)
#         t1 = time.time()
#         iterator = [(a_i,b_i) for a_i, b_i in zip(a,b)]
#         t2 = time.time()
#         print(f'Iterator: {iterator} Done in {t2-t1:.3f} s')
#         with Pool(processes=4) as pool:
#             x = pool.starmap(f, iterator)
#     else:
#         x = np.zeros(Nb_GRBs)
#         for i in range(Nb_GRBs):
#             x[i] = f_test(a[i], b[i], c)
#     return x


# if __name__ == '__main__':
#     import cosmology as cs
#     Nb_GRBs = 10
#     L = np.logspace(48, 55, Nb_GRBs)
#     z = np.linspace(0.01, 6, Nb_GRBs)
#     cosmo = cs.create_cosmology()
#     D_L = cs.Lum_dist(z, cosmo)
#     Ep = np.logspace(1, 4, Nb_GRBs)
#     alpha = 0.6*np.ones(Nb_GRBs)
#     beta = 2.5*np.ones(Nb_GRBs)
#     ktild = (2.0-alpha) * (beta-2.0) / (beta-alpha)
#     spec = 'BPL'

#     t1 = time.time()
#     pflx = pht_flux(L, z, Ep, D_L, alpha, beta, ktild, Emin=50, Emax=300, spec=spec, f90=False)
#     t2 = time.time()
#     print(f"Without parallelization: pflx calculated in {1000*(t2-t1):.3f} ms")
#     # print(f"{pflx}")

#     t1 = time.time()
#     pflx_para = pht_flux(L, z, Ep, D_L, alpha, beta, ktild, Emin=50, Emax=300, spec=spec, f90=False, para=True)
#     t2 = time.time()
#     print(f"With parallelization: pflx calculated in {1000*(t2-t1):.3f} ms")
#     # print(f"{pflx_para}")
#     import matplotlib.pyplot as plt
#     plt.scatter(pflx, pflx_para)
#     plt.show()
