import numpy as np

# Molecular weight [g/mol]
M_CH4 = 16
M_CO = 28
M_CO2 = 44
M_H2 = 2
M_H2O = 18

# Gas viscosity coefficients (see Table S1 in Agu 2019)
# coefficients listed in order of H2, CH4, CO, CO2, H2O
Amu = np.array([27.758, 3.844, 23.811, 11.811, -36.826])
Bmu = np.array([2.120, 4.0112, 5.3944, 4.9838, 4.290]) * 1e-1
Cmu = np.array([-0.3280, -1.4303, -1.5411, -1.0851, -0.1620]) * 1e-4

# Gas specific heat capacity coefficients (see Table S2 in Agu 2019)
# coefficients listed in order of H2, CH4, CO, CO2, H2O
Acp = np.array([25.399, 34.942, 29.556, 27.437, 33.933])
Bcp = np.array([20.178, -39.957, -6.5807, 42.315, -8.4186]) * 1e-3
Ccp = np.array([-3.8549, 19.184, 2.0130, -1.9555, 2.9906]) * 1e-5
Dcp = np.array([3.188, -15.303, -1.2227, 0.39968, -1.7825]) * 1e-8
Ecp = np.array([-8.7585, 39.321, 2.2617, -0.29872, 3.6934]) * 1e-12

# Gas thermal conductivity coefficients (see Table S3 in Agu 2019)
# coefficients listed in order of H2, CH4, CO, CO2, H2O
Ak = np.array([3.951, -0.935, 0.158, -1.200, 0.053]) * 1e-2
Bk = np.array([4.5918, 1.4028, 0.82511, 1.0208, 0.47093]) * 1e-4
Ck = np.array([-6.4933, 3.3180, 1.9081, -2.2403, 4.9551]) * 1e-8


def calc_dP(params, dx, ef, Mg, rhobg, Tg):
    """
    Calculate pressure drop along the reactor.
    """
    N = params['N']
    Np = params['Np']
    R = 8.314

    # volume fraction of gas in bed and freeboard [-]
    afg = np.ones(N)
    afg[0:Np] = ef

    # density of gas along reactor axis [kg/m³]
    rhog = rhobg / afg

    # pressure along reactor axis [Pa]
    P = R * rhog * Tg / Mg * 1e3

    # pressure drop along the reactor
    DP = -afg[0:N - 1] / dx[0:N - 1] * (P[1:N] - P[0:N - 1])

    return P, DP


def calc_rhobgav(N, rhobg):
    """
    Calculate the average gas mass concentration.
    """

    # average gas mass concentration [kg/m³]
    rhob_gav = np.zeros(N)
    rhob_gav[0:N - 1] = 0.5 * (rhobg[0:N - 1] + rhobg[1:N])
    rhob_gav[N - 1] = rhobg[N - 1]

    return rhob_gav


def calc_mix_props(rhob_ch4, rhob_co, rhob_co2, rhob_g, rhob_h2, rhob_h2o, rhob_t, Tg):
    """
    Calculate gas mixture properties along the reactor.
    """

    # Molecular weights
    M = np.array([[M_H2], [M_CH4], [M_CO], [M_CO2], [M_H2O]])

    # Mass fractions
    rhobx = np.array([rhob_h2, rhob_ch4, rhob_co, rhob_co2, rhob_h2o])
    yx = rhobx / rhob_g

    # Mole fractions
    xg = (yx / M) / sum(yx / M)

    # Viscosity
    mux = (Amu[:, None] + Bmu[:, None] * Tg + Cmu[:, None] * Tg**2) * 1e-7

    # Thermal conductivity
    kx = Ak[:, None] + Bk[:, None] * Tg + Ck[:, None] * Tg**2

    # Heat capacity
    cpx = Acp[:, None] + Bcp[:, None] * Tg + Ccp[:, None] * Tg**2 + Dcp[:, None] * Tg**3 + Ecp[:, None] * Tg**4

    # Calculate mixture properties
    Mg = sum(xg * M)
    mu = sum(xg * mux * M**0.5) / sum(xg * M**0.5)
    cpgm = sum(xg * cpx)
    kg = (sum(xg / kx))**(-1)

    cpt = -100 + 4.40 * Tg - 1.57e-3 * Tg**2
    cpgg = cpgm / Mg * 1e3
    yt = rhob_t / rhob_g
    cpg = yt * cpt + (1 - yt) * cpgg
    Pr = cpg * mu / kg

    return Mg, Pr, cpg, cpgm, kg, mu, xg


def calc_fluidization(params, Mg, Tg):
    """
    Calculate fluidization properties. This method must be called after
    the `_calc_mix_props()` method.
    """
    Ab = params['Ab']
    Db = params['Db']
    Lmf = params['Lmf']
    Lsi = params['Lsi']
    Np = params['Np']
    Pin = params['Pin']
    SB = params['SB']
    Tgin = params['Tgin']
    dp = params['dp']
    emf = params['emf']
    ms_dot = params['msdot'] / 3600
    rhop = params['rhop']
    R = 8.314
    g = 9.81

    Tgm = np.mean(np.append(Tg[0:Np], Tgin))
    Tgi = max(Tgin, Tgm)
    muin = (Amu[4] + Bmu[4] * Tgi + Cmu[4] * Tgi**2) * 1e-7

    Mgi = np.mean(Mg[0:Np])
    rhogi = Pin * Mgi / (R * Tgi) * 1e-3

    Ar = dp**3 * rhogi * (rhop - rhogi) * g / muin**2
    Rem = -33.67 + (33.67**2 + 0.0408 * Ar)**0.5
    umf = Rem * muin / (rhogi * dp)
    Umsr = (np.exp(-0.5405 * Lsi / Db) * (4.294e3 / Ar + 1.1) + 3.676e2 * Ar**(-1.5) + 1)

    mfgin = SB * ms_dot / Ab
    Ugin = mfgin / rhogi

    Drbs = 1
    Rrb = (1 - 0.103 * (Umsr * umf - umf)**(-0.362) * Drbs)**(-1)
    Rrs = (1 - 0.305 * (Ugin - umf)**(-0.362) * Db**0.48)**(-1)
    Dbr = 5.64e-4 / (Db * Lmf) * (1 + 27.2 * (Ugin - umf))**(1 / 3) * ((1 + 6.84 * Lmf)**2.21 - 1)

    if Dbr < Drbs:
        Re = (1 - 0.103 * (Ugin - umf)**(-0.362) * Dbr)**(-1)
    else:
        Re = Rrb * Rrs

    De = Re - 1
    if np.isnan(De) or De <= 0:
        De = 0.05

    ef = 1 - (1 - emf) / (De + 1)
    Lp = (De + 1) * Lmf

    return Lp, ef, umf


def mfg_terms(params, ds, dx, ef, Lp, mfg, mu, rhob_g, rhob_gav, rhob_s, rhos, sfc, Sg, v):
    """
    Source terms for calculating gas mass flux.
    """
    Db = params['Db']
    Ls = params['Ls']
    N = params['N']
    Np = params['Np']
    N1 = params['N1']
    dp = params['dp']
    ef0 = params['ef0']
    msdot = params['msdot'] / 3600
    phi = params['phi']
    rhop = params['rhop']

    g = 9.81

    epb = (1 - ef0) * Ls / Lp

    # volume fraction of gas in bed and freeboard [-]
    afg = np.ones(N)
    afg[0:Np] = ef

    # density of gas along reactor axis [kg/m³]
    rhog = rhob_g / afg

    # gas velocity along the reactor [m/s]
    ug = mfg / rhob_gav

    # drag coefficient
    Re_dc = rhog * np.abs(-ug - v) * ds / mu

    Cd = (
        24 / Re_dc * (1 + 8.1716 * Re_dc**(0.0964 + 0.5565 * sfc) * np.exp(-4.0655 * sfc))
        + Re_dc * 73.69 / (Re_dc + 5.378 * np.exp(6.2122 * sfc)) * np.exp(-5.0748 * sfc)
    )

    # bed cross-sectional area [m²]
    Ab = (np.pi / 4) * (Db**2)

    vin = max(v[N1 - 1], ug[N1 - 1])
    rhobbin = msdot / (vin * Ab)

    # average bulk density of fuel particles in each reactor cell [kg/m³]
    rhosbav = np.zeros(N)
    rhosbav[0:N - 1] = 0.5 * (rhob_s[0:N - 1] + rhob_s[1:N])
    rhosbav[N - 1] = 0.5 * (rhobbin + rhob_s[N - 1])

    Reg = rhob_gav * ug * Db / mu

    fg = np.zeros(N)

    for i in range(N):
        if Reg[i] <= 2300:
            fg[i] = 16 / Reg[i]
        else:
            fg[i] = 0.079 / Reg[i]**0.25

    Sgav = np.zeros(N)
    Sgav[0:N - 1] = 0.5 * (Sg[0:N - 1] + Sg[1:N])
    Sgav[N - 1] = Sg[N - 1]

    Smgg = Sgav
    Smgp = 150 * epb**2 * mu / (ef * (phi * dp)**2) + 1.75 * epb / (phi * dp) * rhog * ug
    Smgs = (3 / 4) * rhosbav * (rhog / rhos) * (Cd / ds) * np.abs(-ug - v)
    SmgG = g * (epb * afg * rhop - rhob_gav)
    SmgF = 2 / Db * fg * rhob_gav * np.abs(ug) * ug
    SmgV = SmgG + Smgs * (ug + v) - (Smgp - Smgg) * ug - SmgF

    Cmf = -1 / (2 * dx[1:N - 1]) * ((mfg[2:N] + mfg[1:N - 1]) * ug[1:N - 1] - (mfg[1:N - 1] + mfg[0:N - 2]) * ug[0:N - 2])

    return Cmf, Smgg, SmgV


def mfg_rate(params, Cmf, dx, DP, mfg, rhob_gav, Smgg, SmgV):
    """
    Gas mass flux rate ∂ṁfg/∂t.
    """
    N = params['N']
    Np = params['Np']
    mfgin = params['mfgin']
    rhob_gin = params['rhob_gin']

    # gas velocity along the reactor [m/s]
    ug = mfg / rhob_gav

    # ∂ṁfg/∂t along height of the reactor
    dmfgdt = np.zeros(N)

    # at gas inlet, bottom of reactor
    Cmf1 = -1 / (2 * dx[0]) * ((mfg[1] + mfg[0]) * ug[0] - (mfg[0] + mfgin) * mfgin / rhob_gin)
    Smg1 = Cmf1 + SmgV[0]
    dmfgdt[0] = Smg1 + DP[0]

    # in the bed
    Smg = Cmf + SmgV[1:N - 1]
    dmfgdt[1:Np + 1] = Smg[0:Np] + DP[1:Np + 1]

    # in the bed top and in the freeboard
    Smgf = Cmf[Np - 1:] + Smgg[Np:N - 1] * ug[Np:N - 1] + DP[Np:N - 1]
    dmfgdt[Np:N - 1] = Smgf

    # at top of reactor
    SmgfN = -1 / dx[N - 1] * mfg[N - 1] * (ug[N - 1] - ug[N - 2]) + Smgg[N - 1] * ug[N - 1]
    dmfgdt[N - 1] = SmgfN

    return dmfgdt


def tg_rate(params, cpg, ds, dx, ef, kg, Lp, mfg, mu, Pr, qgs, rhob_g, rhob_gav, rhob_s, rhos, Tg, Tp, Ts, Tw, v):
    """
    Gas temperature rate ∂T𝗀/∂t.
    """
    Db = params['Db']
    Dwi = params['Dwi']
    Dwo = params['Dwo']
    Ls = params['Ls']
    N = params['N']
    Np = params['Np']
    Tgin = params['Tgin']
    dp = params['dp']
    ef0 = params['ef0']
    kw = params['kw']
    phi = params['phi']

    # volume fraction of gas in bed and freeboard [-]
    afg = np.ones(N)
    afg[0:Np] = ef

    # density of gas along reactor axis [kg/m³]
    rhog = rhob_g / afg

    # gas velocity along the reactor [m/s]
    ug = mfg / rhob_gav

    Re_dc = abs(rhog) * abs(-ug - v) * ds / mu
    Nud = 2 + 0.6 * Re_dc**0.5 * Pr**0.33
    hs = Nud * kg / ds

    Rep = abs(rhog) * np.abs(ug) * dp / mu
    Nup = (
        (7 - 10 * afg + 5 * afg**2) * (1 + 0.7 * Rep**0.2 * Pr**0.33)
        + (1.33 - 2.4 * afg + 1.2 * afg**2) * Rep**0.7 * Pr**0.33
    )
    epb = (1 - ef0) * Ls / Lp
    hp = 6 * epb * kg * Nup / (phi * dp**2)
    Uhb = 1 / (4 / (np.pi * Dwi * hp) + np.pi * Dwi / (2 * kw) * np.log(Dwo / Dwi))

    qg = -6 * hs * rhob_s / (rhos * ds) * (Tg - Ts) - hp * (Tg - Tp) + 4 / Db * Uhb * (Tw - Tg)

    # - - -

    Cg = rhob_g * cpg

    # - - -

    ReD = abs(rhog) * np.abs(ug) * Db / mu
    Nuf = 0.023 * ReD**0.8 * Pr**0.4
    hf = Nuf * kg / Db
    Uhf = 1 / (1 / hf + np.pi * Dwi / (2 * kw) * np.log(Dwo / Dwi))

    # - - -

    # ∂T𝗀/∂t along height of the reactor [K]
    dtgdt = np.zeros(N)

    dtgdt[0] = -ug[0] / (dx[0]) * (Tg[0] - Tgin) + (-qgs[0] + qg[0]) / Cg[0]

    dtgdt[1:Np] = -ug[1:Np] / dx[1:Np] * (Tg[1:Np] - Tg[0:Np - 1]) + (-qgs[1:Np] + qg[1:Np]) / Cg[1:Np]

    dtgdt[Np:N] = (
        -ug[Np:N] / dx[Np:N] * (Tg[Np:N] - Tg[Np - 1:N - 1])
        - (qgs[Np:N] - 4 / Db * Uhf[Np:N] * (Tw[Np:N] - Tg[Np:N])) / Cg[Np:N]
    )

    return dtgdt


def rhobg_rate(params, dx, mfg, Sg):
    """
    Gas bulk density rate ∂ρ𝗀/∂t.
    """
    N = params['N']
    mfgin = params['mfgin']

    drhobgdt = np.zeros(N)
    drhobgdt[0] = -(mfg[0] - mfgin) / dx[0] + Sg[0]
    drhobgdt[1:N] = -(mfg[1:N] - mfg[0:N - 1]) / dx[1:N] + Sg[1:N]

    return drhobgdt


def rhobh2o_rate(params, dx, mfg, rhob_g, rhob_h2o, Sh2o):
    """
    H₂O mass concentration rate ∂ρH₂O/∂t.
    """
    N = params['N']
    ugin = params['ugin']
    rhob_gin = params['rhob_gin']

    rhog_in = rhob_gin
    rhobh2o_in = rhog_in

    yH2O = rhob_h2o / rhob_g

    drhobh2o_dt = np.zeros(N)
    drhobh2o_dt[0] = -(yH2O[0] * mfg[0] - rhobh2o_in * ugin) / dx[0] + Sh2o[0]
    drhobh2o_dt[1:N] = -(yH2O[1:N] * mfg[1:N] - yH2O[0:N - 1] * mfg[0:N - 1]) / dx[1:N] + Sh2o[1:N]

    return drhobh2o_dt


def rhobh2_rate(params, dx, mfg, rhob_g, rhob_h2, Sh2):
    """
    here
    """
    N = params['N']
    ugin = params['ugin']

    rhob_h2in = 0
    yH2 = rhob_h2 / rhob_g

    drhobh2_dt = np.zeros(N)
    drhobh2_dt[0] = -(yH2[0] * mfg[0] - rhob_h2in * ugin) / dx[0] + Sh2[0]
    drhobh2_dt[1:N] = -(yH2[1:N] * mfg[1:N] - yH2[0:N - 1] * mfg[0:N - 1]) / dx[1:N] + Sh2[1:N]

    return drhobh2_dt


def rhobch4_rate(params, dx, mfg, rhob_g, rhob_ch4, Sch4):
    """
    here
    """
    N = params['N']
    ugin = params['ugin']

    rhob_ch4in = 0
    yCH4 = rhob_ch4 / rhob_g

    drhobch4_dt = np.zeros(N)
    drhobch4_dt[0] = -(yCH4[0] * mfg[0] - rhob_ch4in * ugin) / dx[0] + Sch4[0]
    drhobch4_dt[1:N] = -(yCH4[1:N] * mfg[1:N] - yCH4[0:N - 1] * mfg[0:N - 1]) / dx[1:N] + Sch4[1:N]

    return drhobch4_dt


def rhobco_rate(params, dx, mfg, rhob_g, rhob_co, Sco):
    """
    here
    """
    N = params['N']
    ugin = params['ugin']

    rhob_coin = 0
    yCO = rhob_co / rhob_g

    drhobco_dt = np.zeros(N)
    drhobco_dt[0] = -(yCO[0] * mfg[0] - rhob_coin * ugin) / dx[0] + Sco[0]
    drhobco_dt[1:N] = -(yCO[1:N] * mfg[1:N] - yCO[0:N - 1] * mfg[0:N - 1]) / dx[1:N] + Sco[1:N]

    return drhobco_dt


def rhobco2_rate(params, dx, mfg, rhob_g, rhob_co2, Sco2):
    """
    here
    """
    N = params['N']
    ugin = params['ugin']

    rhob_co2in = 0
    yCO2 = rhob_co2 / rhob_g

    drhobco2_dt = np.zeros(N)
    drhobco2_dt[0] = -(yCO2[0] * mfg[0] - rhob_co2in * ugin) / dx[0] + Sco2[0]
    drhobco2_dt[1:N] = -(yCO2[1:N] * mfg[1:N] - yCO2[0:N - 1] * mfg[0:N - 1]) / dx[1:N] + Sco2[1:N]

    return drhobco2_dt


def rhobt_rate(params, dx, mfg, rhob_g, rhob_t, St):
    """
    here
    """
    N = params['N']
    ugin = params['ugin']

    rhob_tin = 0
    yt = rhob_t / rhob_g

    drhobt_dt = np.zeros(N)
    drhobt_dt[0] = -(yt[0] * mfg[0] - rhob_tin * ugin) / dx[0] + St[0]
    drhobt_dt[1:N] = -(yt[1:N] * mfg[1:N] - yt[0:N - 1] * mfg[0:N - 1]) / dx[1:N] + St[1:N]

    return drhobt_dt
