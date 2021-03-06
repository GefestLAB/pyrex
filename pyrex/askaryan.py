"""
Module containing Askaryan model signals classes.

Contains various Askaryan models based in both the frequency and time domains.
All classes inherit from the Signal class, meaning they must all be converted
into the time domain at the end of initialization.

"""

import logging
import numpy as np
import scipy.signal
import scipy.fftpack
from pyrex.signals import Signal
from pyrex.ice_model import ice

logger = logging.getLogger(__name__)


class ZHSAskaryanSignal(Signal):
    """
    Class for generating Askaryan signals according to ZHS parameterization.

    Stores the time-domain information for an Askaryan electric field (V/m)
    produced by the electromagnetic shower initiated by a neutrino.

    Parameters
    ----------
    times : array_like
        1D array of times (s) for which the signal is defined.
    particle : Particle
        ``Particle`` object responsible for the shower which produces the
        Askaryan signal. Should have an ``energy`` in GeV, ``vertex`` in m,
        and ``id``, plus an ``interaction`` with an ``em_frac`` and
        ``had_frac``.
    viewing_angle : float
        Observation angle (radians) measured relative to the shower axis.
    viewing_distance : float, optional
        Distance (m) between the shower vertex and the observation point (along
        the ray path).
    ice_model : optional
        The ice model to be used for describing the index of refraction of the
        medium.
    t0 : float, optional
        Pulse offset time (s), i.e. time at which the shower takes place.

    Attributes
    ----------
    times, values : ndarray
        1D arrays of times (s) and corresponding values which define the signal.
    value_type : Signal.Type.field
        Type of signal, representing the units of the values.
    Type : Enum
        Different value types available for `value_type` of signal objects.
    energy : float
        Energy (GeV) of the electromagnetic shower producing the pulse.
    vector_potential
    dt
    frequencies
    spectrum
    envelope

    Raises
    ------
    ValueError
        If the `particle` object is not a neutrino or antineutrino with a
        charged-current or neutral-current interaction.

    See Also
    --------
    Signal : Base class for time-domain signals.
    pyrex.Particle : Class for storing particle attributes.

    Notes
    -----
    Calculates the Askaryan signal based on the ZHS parameterization [1]_.
    Uses equations 20 and 21 to calculate the electric field close to the
    Cherenkov angle.

    References
    ----------
    .. [1] E. Zas, F. Halzen, T. Stanev, "Electromagnetic pulses from
        high-energy showers: implications for neutrino detection", Physical
        Review D **45**, 362-376 (1992). :doi:`10.1103/PhysRevD.45.362`

    """
    def __init__(self, times, particle, viewing_angle, viewing_distance=1,
                 ice_model=ice, t0=0):
        # Theta should represent the angle from the shower axis, and so should
        # always be positive
        theta = np.abs(viewing_angle)

        if theta > np.pi:
            raise ValueError("Angles greater than 180 degrees not supported")

        # Calculate shower energy based on particle's total shower fractions
        self.energy = particle.energy * (particle.interaction.em_frac +
                                         particle.interaction.had_frac)

        # Fail gracefully if there is no EM shower (the energy is zero)
        if self.energy==0:
            super().__init__(times, np.zeros(len(times)),
                             value_type=self.Type.field)
            return

        # Calculate index of refraction at the shower position for the
        # Cherenkov angle calculation and others
        n = ice_model.index(particle.vertex[2])

        # Calculate theta_c = arccos(1/n)
        theta_c = np.arccos(1/n)

        # Parameterization relative frequency value
        nu_0 = 500e6

        # Calculate dt of times array
        dt = times[1] - times[0]

        # Calculate frequencies for frequency-domain calculations
        freqs = scipy.fftpack.fftfreq(len(times), d=dt)

        # Field as a function of frequency at Cherenkov angle (ZHS equation 20)
        ratio = np.abs(freqs)/nu_0
        e_omega = 1.1e-7 * self.energy/1000 * ratio * 1/(1 + 0.4*ratio**2)
        e_omega /= viewing_distance

        # Convert to volts per meter per hertz
        # (from volts per meter per megahertz)
        e_omega *= 1e-6

        # Parameterize away from Cherenkov angle using Gaussian peak (eqn 21)
        e_omega *= np.exp(-0.5*((viewing_angle-theta_c)*ratio
                                /np.radians(2.4))**2)

        # Shift the times so the signal comes at t0
        freq_vals = e_omega * np.exp(-1j*2*np.pi*freqs*(t0-times[0]))

        # Normalize the inverse fourier transform by dt so the time-domain
        # amplitude stays the same for different sampling rates
        values = np.real(scipy.fftpack.ifft(freq_vals)) / dt

        super().__init__(times, values, value_type=self.Type.field)



class AVZAskaryanSignal(Signal):
    """
    Class for generating Askaryan signals according to ARVZ parameterization.

    Stores the time-domain information for an Askaryan electric field (V/m)
    produced by the electromagnetic and hadronic showers initiated by a
    neutrino.

    Parameters
    ----------
    times : array_like
        1D array of times (s) for which the signal is defined.
    particle : Particle
        ``Particle`` object responsible for the showers which produce the
        Askaryan signal. Should have an ``energy`` in GeV, ``vertex`` in m,
        and ``id``, plus an ``interaction`` with an ``em_frac`` and
        ``had_frac``.
    viewing_angle : float
        Observation angle (radians) measured relative to the shower axis.
    viewing_distance : float, optional
        Distance (m) between the shower vertex and the observation point (along
        the ray path).
    ice_model : optional
        The ice model to be used for describing the index of refraction of the
        medium.
    t0 : float, optional
        Pulse offset time (s), i.e. time at which the showers take place.

    Attributes
    ----------
    times, values : ndarray
        1D arrays of times (s) and corresponding values which define the signal.
    value_type : Signal.Type.field
        Type of signal, representing the units of the values.
    Type : Enum
        Different value types available for `value_type` of signal objects.
    em_energy : float
        Energy (GeV) of the electromagnetic shower producing the pulse.
    had_energy : float
        Energy (GeV) of the hadronic shower producing the pulse.
    dt
    frequencies
    spectrum
    envelope

    Raises
    ------
    ValueError
        If the `particle` object is not a neutrino or antineutrino with a
        charged-current or neutral-current interaction.

    See Also
    --------
    Signal : Base class for time-domain signals.
    pyrex.Particle : Class for storing particle attributes.

    Notes
    -----
    Calculates the Askaryan signal based on the AVZ parameterization [1]_.
    Matches the NuRadioMC implementation named 'Alvarez2000', including the
    LPM effect correction added based on an earlier paper by Alvarez-Muniz and
    Zas [2]_.

    References
    ----------
    .. [1] J. Alvarez-Muniz et al, "Calculation Methods for Radio Pulses from
        High Energy Showers." Physical Review D **62**, 063001 (2000).
        :arxiv:`astro-ph/0003315` :doi:`10.1103/PhysRevD.62.063001`
    .. [2] J. Alvarez-Muniz & E. Zas, "The LPM effect for EeV hadronic showers
        in ice: implications for radio detection of neutrinos." Physics Letters
        **B434**, 396-406 (1998). :arxiv:`astro-ph/9806098`
        :doi:`10.1016/S0370-2693(98)00905-8`

    """
    def __init__(self, times, particle, viewing_angle, viewing_distance=1,
                 ice_model=ice, t0=0):
        # Theta should represent the angle from the shower axis, and so should
        # always be positive
        theta = np.abs(viewing_angle)

        if theta > np.pi:
            raise ValueError("Angles greater than 180 degrees not supported")

        # Calculate shower energy based on particle's total shower fractions
        self.em_energy = particle.energy * particle.interaction.em_frac
        self.had_energy = particle.energy * particle.interaction.had_frac

        # Calculate index of refraction at the shower position for the
        # Cherenkov angle calculation and others
        n = ice_model.index(particle.vertex[2])

        # Calculate theta_c = arccos(1/n)
        theta_c = np.arccos(1/n)

        # Calculate corresponding frequencies, ignoring zero frequency
        N = len(times)
        dt = times[1]-times[0]
        freqs = np.fft.rfftfreq(N, dt)[1:]

        # LPM effect parameters
        E_lpm = 2e15 # eV
        dThetaEM = (np.radians(2.7) * 500e6 / freqs
                    * (E_lpm / (0.14 * self.em_energy*1e9 + E_lpm)) ** 0.3)

        if self.had_energy==0:
            epsilon = -np.inf
        else:
            epsilon = np.log10(self.had_energy / 1e3)
        dThetaHad = 0
        if (epsilon >= 0 and epsilon <= 2):
            dThetaHad = 500e6 / freqs * (2.07 - 0.33 * epsilon
                                         + 7.5e-2 * epsilon ** 2)
        elif (epsilon > 2 and epsilon <= 5):
            dThetaHad = 500e6 / freqs * (1.74 - 1.21e-2 * epsilon)
        elif (epsilon > 5 and epsilon <= 7):
            dThetaHad = 500e6 / freqs * (4.23 - 0.785 * epsilon
                                         + 5.5e-2 * epsilon ** 2)
        elif epsilon > 7:
            dThetaHad = (500e6 / freqs * (4.23 - 0.785 * 7 + 5.5e-2 * 7 ** 2)
                         * (1 + (epsilon - 7) * 0.075))
        dThetaHad = np.radians(dThetaHad)


        f0 = 1.15e9 # Hz
        em_tmp = np.zeros(len(freqs) + 1)
        had_tmp = np.zeros(len(freqs) + 1)
        # Electromagnetic shower handling
        if particle.interaction.em_frac>0:
            E = (2.53e-7 * self.em_energy/1e3 * freqs / f0
                 / (1 + (freqs / f0) ** 1.44)) # V/m/Hz
            E /= 1e6 # convert to V/m/MHz
            E *= np.sin(theta) / np.sin(theta_c)
            em_tmp[1:] += (E / viewing_distance
                           * np.exp(-np.log(2) *
                                    ((theta - theta_c) / dThetaEM)**2))
        # Hadronic shower handling (when hadronic energy is above 1 TeV)
        if particle.interaction.had_frac>0 and np.any(dThetaHad!=0):
            E = (2.53e-7 * self.had_energy/1e3 * freqs / f0
                / (1 + (freqs / f0) ** 1.44)) # V/m/Hz
            E /= 1e6 # convert to V/m/MHz
            E *= np.sin(theta) / np.sin(theta_c)
            had_tmp[1:] += (E / viewing_distance
                            * np.exp(-np.log(2) *
                                     ((theta - theta_c) / dThetaHad)**2))

            def missing_energy_factor(E_0):
                # Missing energy factor for hadronic cascades
                # Taken from DOI: 10.1016/S0370-2693(98)00905-8
                epsilon = np.log10(E_0/1e3)
                f_epsilon  = -1.27e-2 - 4.76e-2*(epsilon+3)
                f_epsilon += -2.07e-3*(epsilon+3)**2 + 0.52*np.sqrt(epsilon+3)
                return f_epsilon

            had_tmp[1:] *= missing_energy_factor(self.had_energy)


        # Combine showers
        tmp = em_tmp + had_tmp

        # Factor of 0.5 is introduced to compensate the unusual fourier
        # transform normalization used in the ZHS code
        tmp *= 0.5

        # Set phases to 90 degrees
        trace = np.fft.irfft(tmp * np.exp(0.5j * np.pi)) / dt

        # Shift to proper t0
        trace = np.roll(trace, int((t0-times[0]) / dt))

        super().__init__(times, trace, value_type=self.Type.field)


class ARVZAskaryanSignal(Signal):
    """
    Class for generating Askaryan signals according to ARVZ parameterization.

    Stores the time-domain information for an Askaryan electric field (V/m)
    produced by the electromagnetic and hadronic showers initiated by a
    neutrino.

    Parameters
    ----------
    times : array_like
        1D array of times (s) for which the signal is defined.
    particle : Particle
        ``Particle`` object responsible for the showers which produce the
        Askaryan signal. Should have an ``energy`` in GeV, ``vertex`` in m,
        and ``id``, plus an ``interaction`` with an ``em_frac`` and
        ``had_frac``.
    viewing_angle : float
        Observation angle (radians) measured relative to the shower axis.
    viewing_distance : float, optional
        Distance (m) between the shower vertex and the observation point (along
        the ray path).
    ice_model : optional
        The ice model to be used for describing the index of refraction of the
        medium.
    t0 : float, optional
        Pulse offset time (s), i.e. time at which the showers take place.

    Attributes
    ----------
    times, values : ndarray
        1D arrays of times (s) and corresponding values which define the signal.
    value_type : Signal.Type.field
        Type of signal, representing the units of the values.
    Type : Enum
        Different value types available for `value_type` of signal objects.
    em_energy : float
        Energy (GeV) of the electromagnetic shower producing the pulse.
    had_energy : float
        Energy (GeV) of the hadronic shower producing the pulse.
    vector_potential
    dt
    frequencies
    spectrum
    envelope

    Raises
    ------
    ValueError
        If the `particle` object is not a neutrino or antineutrino with a
        charged-current or neutral-current interaction.

    See Also
    --------
    Signal : Base class for time-domain signals.
    pyrex.Particle : Class for storing particle attributes.

    Notes
    -----
    Calculates the Askaryan signal based on the ARVZ parameterization [1]_.
    Uses a Greisen model for the electromagnetic shower profile [2]_, [3]_ and
    a Gaisser-Hillas model for the hadronic shower profile [4]_, [5]_.
    Calculates the electric field from the vector potential using the
    convolution method outlined in section 4 of the ARVZ paper, which results
    in the most efficient calculation of the parameterization.

    References
    ----------
    .. [1] J. Alvarez-Muniz et al, "Practical and accurate calculations
        of Askaryan radiation." Physical Review D **84**, 103003 (2011).
        :arxiv:`1106.6283` :doi:`10.1103/PhysRevD.84.103003`
    .. [2] K. Greisen, "The Extensive Air Showers." Prog. in Cosmic Ray Phys.
        **III**, 1 (1956).
    .. [3] K.D. de Vries et al, "On the feasibility of RADAR detection of
        high-energy neutrino-induced showers in ice." Astropart. Phys. **60**,
        25-31 (2015). :arxiv:`1312.4331`
        :doi:`10.1016/j.astropartphys.2014.05.009`
    .. [4] T.K. Gaisser & A.M. Hillas "Reliability of the Method of Constant
        Intensity Cuts for Reconstructing the Average Development of Vertical
        Showers." ICRC proceedings, 353 (1977).
    .. [5] J. Alvarez-Muniz & E. Zas, "EeV Hadronic Showers in Ice: The LPM
        effect." ICRC proceedings, 17-25 (1999). :arxiv:`astro-ph/9906347`

    """
    def __init__(self, times, particle, viewing_angle, viewing_distance=1,
                 ice_model=ice, t0=0):
        # Calculation of pulse based on https://arxiv.org/pdf/1106.6283v3.pdf
        # Vector potential is given by:
        #   A(theta,t) = convolution(Q(z(1-n*cos(theta))/c)),
        #                            RAC(z(1-n*cos(theta))/c))
        #                * sin(theta) / sin(theta_c) / R / integral(Q(z))
        #                * c / (1-n*cos(theta))

        # Theta should represent the angle from the shower axis, and so should
        # always be positive
        theta = np.abs(viewing_angle)

        if theta > np.pi:
            raise ValueError("Angles greater than 180 degrees not supported")

        # Calculate shower energies based on particle's electromagnetic and
        # hadronic shower fractions
        self.em_energy = particle.energy * particle.interaction.em_frac
        self.had_energy = particle.energy * particle.interaction.had_frac

        # Calculate index of refraction at the shower position for the
        # Cherenkov angle calculation and others
        n = ice_model.index(particle.vertex[2])

        # Calculate the resulting pulse values from an electromagnetic shower
        # and a hadronic shower, then add them
        em_vals = self.shower_signal(times=times, energy=self.em_energy,
                                     profile_function=self.em_shower_profile,
                                     viewing_angle=theta,
                                     viewing_distance=viewing_distance,
                                     n=n, t0=t0)
        had_vals = self.shower_signal(times=times, energy=self.had_energy,
                                      profile_function=self.had_shower_profile,
                                      viewing_angle=theta,
                                      viewing_distance=viewing_distance,
                                      n=n, t0=t0)

        # Note that although len(values) = len(times)-1 (because of np.diff),
        # the Signal class is designed to handle this by zero-padding the values
        super().__init__(times, em_vals+had_vals, value_type=self.Type.field)


    def shower_signal(self, times, energy, profile_function, viewing_angle,
                      viewing_distance, n, t0):
        """
        Calculate the signal values for some shower type.

        Calculates the time-domain values for an Askaryan electric field (V/m)
        produced by a particular shower initiated by a neutrino.

        Parameters
        ----------
        times : array_like
            1D array of times (s) for which the signal is defined.
        energy : float
            Energy (GeV) of the shower.
        profile_function : function
            Function to be used for calculating the longitudinal shower
            profile. Should take a distance (m) and energy (GeV) and return the
            profile value at that depth for a shower of that energy.
        viewing_angle : float
            Observation angle (radians) measured relative to the shower axis.
            Should be positive-valued.
        viewing_distance : float
            Distance (m) between the shower vertex and the observation point
            (along the ray path).
        n : float
            The index of refraction of the ice at the location of the shower.
        t0 : float
            Pulse offset time (s), i.e. time at which the shower takes place.

        Returns
        -------
        array_like
            1D array of values of the signal created by the shower
            corresponding to the given `times`. Length ends up being one less
            than the length of `times` due to implementation.

        """
        # Calculation of pulse based on https://arxiv.org/pdf/1106.6283v3.pdf
        # Vector potential is given by:
        #   A(theta,t) = convolution(Q(z(1-n*cos(theta))/c)),
        #                            RAC(z(1-n*cos(theta))/c))
        #                * sin(theta) / sin(theta_c) / R / integral(Q(z))
        #                * c / (1-n*cos(theta))

        # Fail gracefully if there is no shower (the energy is zero)
        if energy==0:
            return np.zeros(len(times)-1)

        theta = viewing_angle

        # Conversion factor from z to t for RAC:
        # (1-n*cos(theta)) / c
        z_to_t = (1 - n*np.cos(theta))/3e8

        # Calculate the time step and the corresponding z-step
        dt = times[1] - times[0]

        # Calculate the corresponding z-step (dz = dt / z_to_t)
        # If the z-step is too large compared to the expected shower maximum
        # length, then the result will be bad. Set dt_divider so that
        # dz / max_length <= 0.1 (with dz=dt/z_to_t)
        dt_divider = int(np.abs(10*dt/self.max_length(energy)/z_to_t)) + 1
        dz = dt / dt_divider / z_to_t
        if dt_divider!=1:
            logger.debug("z-step of %g too large; dt_divider changed to %g",
                         dt / z_to_t, dt_divider)

        # Create the charge-profile array up to 2.5 times the nominal
        # shower maximum length (to reduce errors).
        z_max = 2.5*self.max_length(energy)
        n_Q = int(np.abs(z_max/dz))
        z_Q_vals = np.arange(n_Q) * np.abs(dz)
        Q = profile_function(z_Q_vals, energy)

        # Fail gracefully if the energy is less than the critical energy for
        # shower formation (i.e. all Q values are zero)
        if np.all(Q==0) and len(Q)>0:
            return np.zeros(len(times)-1)

        # Calculate RAC at a specific number of t values (n_RAC) determined so
        # that the full convolution will have the same size as the times array,
        # when appropriately rescaled by dt_divider.
        # If t_RAC_vals does not include a reasonable range around zero
        # (typically because n_RAC is too small), errors occur. In that case
        # extra points are added at the beginning and/or end of RAC.
        # If n_RAC is too large, the convolution can take a very long time.
        # In that case, points are removed from the beginning and/or end of RAC.
        t_tolerance = 10e-9
        t_start = times[0] - t0
        n_extra_beginning = int((t_start+t_tolerance)/dz/z_to_t) + 1
        n_extra_end = (int((t_tolerance-t_start)/dz/z_to_t) + 1
                       + n_Q - len(times)*dt_divider)
        n_RAC = (len(times)*dt_divider + 1 - n_Q
                 + n_extra_beginning + n_extra_end)
        t_RAC_vals = (np.arange(n_RAC) * dz * z_to_t
                      + t_start - n_extra_beginning * dz * z_to_t)
        RA_C = self.RAC(t_RAC_vals, energy)

        # Convolve Q and RAC to get unnormalized vector potential
        if n_Q*n_RAC>1e6:
            logger.debug("convolving %i Q points with %i RA_C points",
                         n_Q, n_RAC)
        convolution = scipy.signal.convolve(Q, RA_C, mode='full')

        # Adjust convolution by zero-padding or removing values according to
        # the values added/removed at the beginning and end of RA_C
        if n_extra_beginning<0:
            convolution = np.concatenate((np.zeros(-n_extra_beginning),
                                          convolution))
        else:
            convolution = convolution[n_extra_beginning:]
        if n_extra_end<=0:
            convolution = np.concatenate((convolution,
                                          np.zeros(-n_extra_end)))
        else:
            convolution = convolution[:-n_extra_end]

        # Reduce the number of values in the convolution based on the dt_divider
        # so that the number of values matches the length of the times array.
        # It's possible that this should be using scipy.signal.resample instead
        # TODO: Figure that out
        convolution = convolution[::dt_divider]

        # Calculate LQ_tot (the excess longitudinal charge along the showers)
        LQ_tot = np.trapz(Q, dx=dz)

        # Calculate sin(theta_c) = sqrt(1-cos^2(theta_c)) = sqrt(1-1/n^2)
        sin_theta_c = np.sqrt(1 - 1/n**2)

        # Scale the convolution by the necessary factors to get the true
        # vector potential A
        # z_to_t and dt_divider are divided based on trial and error to correct
        # the normalization. They are not proven nicely like the other factors
        A = (convolution * -1 * np.sin(theta) / sin_theta_c / LQ_tot
             / z_to_t / dt_divider)

        # Not sure why, but multiplying A by -dt is necessary to fix
        # normalization and dependence of amplitude on time spacing.
        # Since E = -dA/dt = np.diff(A) / -dt, we can skip multiplying
        # and later dividing by dt to save a little computational effort
        # (at the risk of more cognitive effort when deciphering the code)
        # So, to clarify, the above statement should have "* -dt" at the end
        # to be the true value of A, and the below would then have "/ -dt"

        # Calculate electric field by taking derivative of vector potential,
        # and divide by the viewing distance (R)
        return np.diff(A) / viewing_distance


    @property
    def vector_potential(self):
        """
        The vector potential of the signal.

        Recovered from the electric field, mostly just for testing purposes.

        """
        return np.cumsum(np.concatenate(([0],self.values)))[:-1] * -self.dt


    @staticmethod
    def RAC(time, energy):
        """
        Calculates R*A_C at the given time and energy.

        The R*A_C value is the observation distance R (m) times the vector
        potential (V*s/m) at the Cherenkov angle.

        Parameters
        ----------
        time : array_like
            Time (s) at which to calculate the R*A_C value.
        energy : float
            Energy (GeV) of the shower.

        Returns
        -------
        array_like
            The R*A_C value (V*s) at the given time.

        Notes
        -----
        Based on equation 16 of the ARVZ paper [1]_. This parameterization
        is only described for electromagnetic showers, but in the absence of
        a different parameterization for hadronic showers this one is used for
        both cases.

        References
        ----------
        .. [1] J. Alvarez-Muniz et al, "Practical and accurate calculations
            of Askaryan radiation." Physical Review D **84**, 103003 (2011).
            :arxiv:`1106.6283` :doi:`10.1103/PhysRevD.84.103003`

        """
        # Get absolute value of time in nanoseconds
        ta = np.abs(time) * 1e9
        rac = np.zeros_like(time)
        rac[time>=0] = (-4.5e-17 * energy *
                        (np.exp(-ta[time>=0]/0.057) + (1+2.87*ta[time>=0])**-3))
        rac[time<0] = (-4.5e-17 * energy *
                       (np.exp(-ta[time<0]/0.030) + (1+3.05*ta[time<0])**-3.5))
        return rac

    @staticmethod
    def em_shower_profile(z, energy, density=0.92, crit_energy=7.86e-2,
                          rad_length=36.08):
        """
        Calculates the electromagnetic shower longitudinal charge profile.

        The longitudinal charge profile is calculated for a given distance,
        shower energy, density, critical energy, and electron radiation length
        in ice.

        Parameters
        ----------
        z : array_like
            Distance (m) along the shower at which to calculate the charge.
        energy : float
            Energy (GeV) of the shower.
        density : float, optional
            Density (g/cm^3) of ice.
        crit_energy : float, optional
            Critical energy (GeV) for shower formation.
        rad_length : float, optional
            Electron radiation length (g/cm^2) in ice.

        Returns
        -------
        array_like
            The charge (C) at the given distance along the shower.

        Notes
        -----
        Profile calculated by the Greisen model [1]_, based on equations 24 and
        25 of the radar feasibility paper [2]_.

        References
        ----------
        .. [1] K. Greisen, "The Extensive Air Showers." Prog. in Cosmic Ray
            Phys. **III**, 1 (1956).
        .. [2] K.D. de Vries et al, "On the feasibility of RADAR detection of
            high-energy neutrino-induced showers in ice." Astropart. Phys.
            **60**, 25-31 (2015). :arxiv:`1312.4331`
            :doi:`10.1016/j.astropartphys.2014.05.009`

        """
        N = np.zeros_like(z)

        # Below critical energy, no shower
        if energy<=crit_energy:
            return N

        # Depth calculated by "integrating" the density along the shower path
        # (in g/cm^2)
        x = 100 * z * density
        x_ratio = x / rad_length
        e_ratio = energy / crit_energy

        # Shower age
        s = 3 * x_ratio / (x_ratio + 2*np.log(e_ratio))

        # Number of particles
        N[z>0] = (0.31 * np.exp(x_ratio[z>0] * (1 - 1.5*np.log(s[z>0])))
                  / np.sqrt(np.log(e_ratio)))

        return N * 1.602e-19

    @staticmethod
    def had_shower_profile(z, energy, density=0.92, crit_energy=17.006e-2,
                           rad_length=39.562, int_length=113.03,
                           scale_factor=0.11842):
        """
        Calculates the hadronic shower longitudinal charge profile.

        The longitudinal charge profile is calculated for a given distance,
        density, critical energy, hadron radiation length, and interaction
        length in ice, plus a scale factor for the number of particles.

        Parameters
        ----------
        z : array_like
            Distance (m) along the shower at which to calculate the charge.
        energy : float
            Energy (GeV) of the shower.
        density : float, optional
            Density (g/cm^3) of ice.
        crit_energy : float, optional
            Critical energy (GeV) for shower formation.
        rad_length : float, optional
            Hadron radiation length (g/cm^2) in ice.
        int_length : float, optional
            Interaction length (g/cm^2) in ice.
        scale_factor : float, optional
            Scale factor S_0 which multiplies the number of particles in the
            shower.

        Returns
        -------
        array_like
            The charge (C) at the given distance along the shower.

        Notes
        -----
        Profile calculated by the Gaisser-Hillas model [1]_, based on equation
        1 of the Alvarez hadronic shower paper [2]_.

        References
        ----------
        .. [1] T.K. Gaisser & A.M. Hillas "Reliability of the Method of
            Constant Intensity Cuts for Reconstructing the Average Development
            of Vertical Showers." ICRC proceedings, 353 (1977).
        .. [2] J. Alvarez-Muniz & E. Zas, "EeV Hadronic Showers in Ice: The LPM
            effect." ICRC proceedings, 17-25 (1999). :arxiv:`astro-ph/9906347`

        """
        N = np.zeros_like(z)

        # Below critical energy, no shower
        if energy<=crit_energy:
            return N

        # Calculate shower depth and shower maximum depth in g/cm^2
        x = 100 * z * density
        e_ratio = energy / crit_energy
        x_max = rad_length * np.log(e_ratio)

        # Number of particles
        N[z>0] = (scale_factor * e_ratio * (x_max - int_length) / x_max
                  * (x[z>0] / (x_max - int_length))**(x_max / int_length)
                  * np.exp((x_max - x[z>0])/int_length - 1))

        return N * 1.602e-19

    @staticmethod
    def max_length(energy, density=0.92, crit_energy=7.86e-2,
                   rad_length=36.08):
        """
        Calculates the depth of a particle shower maximum.

        The shower depth of a shower maximum is calculated for a given density,
        critical energy, and particle radiation length in ice.

        Parameters
        ----------
        energy : float
            Energy (GeV) of the shower.
        density : float, optional
            Density (g/cm^3) of ice.
        crit_energy : float, optional
            Critical energy (GeV) for shower formation.
        rad_length : float, optional
            Radiation length (g/cm^2) in ice of the particle which makes up the
            shower.

        Returns
        -------
        float
            The depth (m) of the shower maximum for a particle shower.

        """
        # Maximum depth in g/cm^2
        x_max = rad_length * np.log(energy / crit_energy) / np.log(2)

        return 0.01 * x_max / density



# Set the default Askaryan model
AskaryanSignal = ARVZAskaryanSignal