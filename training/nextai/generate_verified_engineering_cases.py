#!/usr/bin/env python3
"""Generate original, deterministic, formula-checked engineering SFT cases.

The generator creates educational calculation examples from explicit analytic
relationships. It does not generate design approvals, code-compliance claims or
native CAD/BIM execution traces.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from typing import Any, Callable

SOURCE_NAME = "Next3D original analytic engineering cases"
SOURCE_LICENSE = "project-authored"
SPLITS = ("train", "validation", "test")


def _round(value: float, digits: int = 5) -> float:
    return round(float(value), digits)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def solve_beam_udl(inputs: dict[str, float]) -> dict[str, Any]:
    length = float(inputs["span_m"])
    w = float(inputs["udl_kN_per_m"])
    modulus_n_mm2 = float(inputs["elastic_modulus_GPa"]) * 1000.0
    inertia_mm4 = float(inputs["second_moment_mm4"])
    length_mm = length * 1000.0
    # 1 kN/m is numerically equal to 1 N/mm.
    delta_mm = 5.0 * w * length_mm**4 / (384.0 * modulus_n_mm2 * inertia_mm4)
    return {
        "values": {
            "reaction_A_kN": _round(w * length / 2.0),
            "reaction_B_kN": _round(w * length / 2.0),
            "maximum_sagging_moment_kN_m": _round(w * length**2 / 8.0),
            "maximum_deflection_mm": _round(delta_mm, 6),
        },
        "units": {
            "reaction_A_kN": "kN",
            "reaction_B_kN": "kN",
            "maximum_sagging_moment_kN_m": "kN·m",
            "maximum_deflection_mm": "mm",
        },
    }


def solve_beam_centre_load(inputs: dict[str, float]) -> dict[str, Any]:
    length = float(inputs["span_m"])
    load_n = float(inputs["central_point_load_kN"]) * 1000.0
    modulus_n_mm2 = float(inputs["elastic_modulus_GPa"]) * 1000.0
    inertia_mm4 = float(inputs["second_moment_mm4"])
    length_mm = length * 1000.0
    delta_mm = load_n * length_mm**3 / (48.0 * modulus_n_mm2 * inertia_mm4)
    load_kn = load_n / 1000.0
    return {
        "values": {
            "reaction_A_kN": _round(load_kn / 2.0),
            "reaction_B_kN": _round(load_kn / 2.0),
            "maximum_sagging_moment_kN_m": _round(load_kn * length / 4.0),
            "maximum_deflection_mm": _round(delta_mm, 6),
        },
        "units": {
            "reaction_A_kN": "kN",
            "reaction_B_kN": "kN",
            "maximum_sagging_moment_kN_m": "kN·m",
            "maximum_deflection_mm": "mm",
        },
    }


def solve_cantilever_tip_load(inputs: dict[str, float]) -> dict[str, Any]:
    length = float(inputs["cantilever_length_m"])
    load_n = float(inputs["tip_load_kN"]) * 1000.0
    modulus_n_mm2 = float(inputs["elastic_modulus_GPa"]) * 1000.0
    inertia_mm4 = float(inputs["second_moment_mm4"])
    length_mm = length * 1000.0
    delta_mm = load_n * length_mm**3 / (3.0 * modulus_n_mm2 * inertia_mm4)
    return {
        "values": {
            "fixed_end_shear_kN": _round(load_n / 1000.0),
            "fixed_end_moment_kN_m": _round(load_n / 1000.0 * length),
            "tip_deflection_mm": _round(delta_mm, 6),
        },
        "units": {
            "fixed_end_shear_kN": "kN",
            "fixed_end_moment_kN_m": "kN·m",
            "tip_deflection_mm": "mm",
        },
    }


def solve_axial_bar(inputs: dict[str, float]) -> dict[str, Any]:
    force_n = float(inputs["axial_force_kN"]) * 1000.0
    area_mm2 = float(inputs["area_mm2"])
    length_mm = float(inputs["length_m"]) * 1000.0
    modulus_n_mm2 = float(inputs["elastic_modulus_GPa"]) * 1000.0
    stress = force_n / area_mm2
    strain = stress / modulus_n_mm2
    elongation_mm = strain * length_mm
    return {
        "values": {
            "normal_stress_MPa": _round(stress, 6),
            "normal_strain": _round(strain, 9),
            "elongation_mm": _round(elongation_mm, 6),
        },
        "units": {
            "normal_stress_MPa": "MPa",
            "normal_strain": "dimensionless",
            "elongation_mm": "mm",
        },
    }


def solve_solid_shaft_torsion(inputs: dict[str, float]) -> dict[str, Any]:
    torque_n_mm = float(inputs["torque_kN_m"]) * 1_000_000.0
    diameter_mm = float(inputs["shaft_diameter_mm"])
    length_mm = float(inputs["shaft_length_m"]) * 1000.0
    shear_modulus_n_mm2 = float(inputs["shear_modulus_GPa"]) * 1000.0
    polar_moment = math.pi * diameter_mm**4 / 32.0
    shear_stress = 16.0 * torque_n_mm / (math.pi * diameter_mm**3)
    twist_rad = torque_n_mm * length_mm / (shear_modulus_n_mm2 * polar_moment)
    return {
        "values": {
            "maximum_shear_stress_MPa": _round(shear_stress, 6),
            "angle_of_twist_rad": _round(twist_rad, 8),
            "angle_of_twist_deg": _round(math.degrees(twist_rad), 6),
        },
        "units": {
            "maximum_shear_stress_MPa": "MPa",
            "angle_of_twist_rad": "rad",
            "angle_of_twist_deg": "degree",
        },
    }


def solve_pipe_continuity(inputs: dict[str, float]) -> dict[str, Any]:
    flow_m3_s = float(inputs["flow_L_per_s"]) / 1000.0
    diameter_m = float(inputs["internal_diameter_mm"]) / 1000.0
    area = math.pi * diameter_m**2 / 4.0
    velocity = flow_m3_s / area
    return {
        "values": {
            "flow_m3_per_s": _round(flow_m3_s, 8),
            "flow_area_m2": _round(area, 8),
            "mean_velocity_m_per_s": _round(velocity, 6),
        },
        "units": {
            "flow_m3_per_s": "m³/s",
            "flow_area_m2": "m²",
            "mean_velocity_m_per_s": "m/s",
        },
    }


def solve_darcy_weisbach(inputs: dict[str, float]) -> dict[str, Any]:
    flow_m3_s = float(inputs["flow_L_per_s"]) / 1000.0
    diameter_m = float(inputs["internal_diameter_mm"]) / 1000.0
    length_m = float(inputs["pipe_length_m"])
    friction_factor = float(inputs["darcy_friction_factor"])
    area = math.pi * diameter_m**2 / 4.0
    velocity = flow_m3_s / area
    head_loss = friction_factor * (length_m / diameter_m) * velocity**2 / (2.0 * 9.80665)
    return {
        "values": {
            "mean_velocity_m_per_s": _round(velocity, 6),
            "darcy_head_loss_m": _round(head_loss, 6),
        },
        "units": {
            "mean_velocity_m_per_s": "m/s",
            "darcy_head_loss_m": "m",
        },
    }


def solve_manning_rectangular(inputs: dict[str, float]) -> dict[str, Any]:
    width = float(inputs["channel_width_m"])
    depth = float(inputs["flow_depth_m"])
    roughness = float(inputs["manning_n"])
    slope = float(inputs["energy_slope"])
    area = width * depth
    wetted_perimeter = width + 2.0 * depth
    hydraulic_radius = area / wetted_perimeter
    velocity = (1.0 / roughness) * hydraulic_radius ** (2.0 / 3.0) * math.sqrt(slope)
    discharge = velocity * area
    return {
        "values": {
            "flow_area_m2": _round(area, 6),
            "hydraulic_radius_m": _round(hydraulic_radius, 6),
            "mean_velocity_m_per_s": _round(velocity, 6),
            "discharge_m3_per_s": _round(discharge, 6),
        },
        "units": {
            "flow_area_m2": "m²",
            "hydraulic_radius_m": "m",
            "mean_velocity_m_per_s": "m/s",
            "discharge_m3_per_s": "m³/s",
        },
    }


def solve_effective_stress(inputs: dict[str, float]) -> dict[str, Any]:
    total_stress = float(inputs["total_vertical_stress_kPa"])
    pore_pressure = float(inputs["pore_water_pressure_kPa"])
    effective = total_stress - pore_pressure
    return {
        "values": {
            "effective_vertical_stress_kPa": _round(effective, 6),
        },
        "units": {
            "effective_vertical_stress_kPa": "kPa",
        },
    }


def solve_consolidation(inputs: dict[str, float]) -> dict[str, Any]:
    cc = float(inputs["compression_index_Cc"])
    height_m = float(inputs["compressible_layer_thickness_m"])
    e0 = float(inputs["initial_void_ratio"])
    sigma0 = float(inputs["initial_effective_stress_kPa"])
    delta_sigma = float(inputs["stress_increment_kPa"])
    final_sigma = sigma0 + delta_sigma
    settlement_m = cc * height_m / (1.0 + e0) * math.log10(final_sigma / sigma0)
    return {
        "values": {
            "final_effective_stress_kPa": _round(final_sigma, 6),
            "primary_consolidation_settlement_mm": _round(settlement_m * 1000.0, 6),
        },
        "units": {
            "final_effective_stress_kPa": "kPa",
            "primary_consolidation_settlement_mm": "mm",
        },
    }


def solve_slab_concrete_quantity(inputs: dict[str, float]) -> dict[str, Any]:
    length = float(inputs["slab_length_m"])
    width = float(inputs["slab_width_m"])
    thickness = float(inputs["slab_thickness_m"])
    volume = length * width * thickness
    return {
        "values": {
            "plan_area_m2": _round(length * width, 6),
            "concrete_volume_m3": _round(volume, 6),
        },
        "units": {
            "plan_area_m2": "m²",
            "concrete_volume_m3": "m³",
        },
    }


def solve_rebar_mass(inputs: dict[str, float]) -> dict[str, Any]:
    diameter_m = float(inputs["bar_diameter_mm"]) / 1000.0
    total_length_m = float(inputs["total_bar_length_m"])
    steel_density = 7850.0
    mass_per_m = steel_density * math.pi * diameter_m**2 / 4.0
    total_mass = mass_per_m * total_length_m
    return {
        "values": {
            "mass_per_metre_kg_per_m": _round(mass_per_m, 6),
            "total_steel_mass_kg": _round(total_mass, 6),
        },
        "units": {
            "mass_per_metre_kg_per_m": "kg/m",
            "total_steel_mass_kg": "kg",
        },
    }


def solve_gear_ratio(inputs: dict[str, float]) -> dict[str, Any]:
    driver_teeth = int(inputs["driver_teeth"])
    driven_teeth = int(inputs["driven_teeth"])
    driver_speed = float(inputs["driver_speed_rpm"])
    ratio = driven_teeth / driver_teeth
    output_speed = driver_speed / ratio
    return {
        "values": {
            "speed_reduction_ratio": _round(ratio, 6),
            "driven_speed_rpm": _round(output_speed, 6),
            "ideal_torque_multiplier": _round(ratio, 6),
        },
        "units": {
            "speed_reduction_ratio": "dimensionless",
            "driven_speed_rpm": "rpm",
            "ideal_torque_multiplier": "dimensionless",
        },
    }


def solve_three_phase_power(inputs: dict[str, float]) -> dict[str, Any]:
    voltage = float(inputs["line_voltage_V"])
    current = float(inputs["line_current_A"])
    power_factor = float(inputs["power_factor"])
    power_w = math.sqrt(3.0) * voltage * current * power_factor
    return {
        "values": {
            "apparent_power_kVA": _round(math.sqrt(3.0) * voltage * current / 1000.0, 6),
            "active_power_kW": _round(power_w / 1000.0, 6),
        },
        "units": {
            "apparent_power_kVA": "kVA",
            "active_power_kW": "kW",
        },
    }


def solve_leveling(inputs: dict[str, float]) -> dict[str, Any]:
    benchmark_rl = float(inputs["benchmark_reduced_level_m"])
    backsight = float(inputs["backsight_m"])
    foresight = float(inputs["foresight_m"])
    height_of_instrument = benchmark_rl + backsight
    point_rl = height_of_instrument - foresight
    return {
        "values": {
            "height_of_instrument_m": _round(height_of_instrument, 6),
            "new_point_reduced_level_m": _round(point_rl, 6),
            "rise_or_fall_m": _round(point_rl - benchmark_rl, 6),
        },
        "units": {
            "height_of_instrument_m": "m",
            "new_point_reduced_level_m": "m",
            "rise_or_fall_m": "m",
        },
    }


def solve_rectangle_section(inputs: dict[str, float]) -> dict[str, Any]:
    breadth = float(inputs["breadth_mm"])
    depth = float(inputs["depth_mm"])
    area = breadth * depth
    inertia = breadth * depth**3 / 12.0
    section_modulus = inertia / (depth / 2.0)
    return {
        "values": {
            "area_mm2": _round(area, 6),
            "second_moment_about_strong_axis_mm4": _round(inertia, 6),
            "elastic_section_modulus_mm3": _round(section_modulus, 6),
        },
        "units": {
            "area_mm2": "mm²",
            "second_moment_about_strong_axis_mm4": "mm⁴",
            "elastic_section_modulus_mm3": "mm³",
        },
    }


def solve_earthwork_average_end_area(inputs: dict[str, float]) -> dict[str, Any]:
    length = float(inputs["section_spacing_m"])
    area_1 = float(inputs["cut_area_1_m2"])
    area_2 = float(inputs["cut_area_2_m2"])
    volume = length * (area_1 + area_2) / 2.0
    return {
        "values": {
            "average_end_area_m2": _round((area_1 + area_2) / 2.0, 6),
            "earthwork_volume_m3": _round(volume, 6),
        },
        "units": {
            "average_end_area_m2": "m²",
            "earthwork_volume_m3": "m³",
        },
    }


GOVERNING_EQUATIONS: dict[str, list[str]] = {
    "solve_beam_udl": [
        "RA = RB = wL/2",
        "Mmax = wL^2/8",
        "delta_max = 5wL^4/(384EI)",
        "1 kN/m = 1 N/mm for the millimetre-based deflection calculation",
    ],
    "solve_beam_centre_load": [
        "RA = RB = P/2",
        "Mmax = PL/4",
        "delta_mid = PL^3/(48EI)",
    ],
    "solve_cantilever_tip_load": [
        "Vfixed = P",
        "Mfixed = PL",
        "delta_tip = PL^3/(3EI)",
    ],
    "solve_axial_bar": [
        "sigma = P/A",
        "epsilon = sigma/E",
        "delta = epsilon*L",
        "1 GPa = 1000 MPa = 1000 N/mm^2",
    ],
    "solve_solid_shaft_torsion": [
        "J = pi*d^4/32",
        "tau_max = 16T/(pi*d^3)",
        "theta = TL/(JG)",
        "Convert T from kN m to N mm and L from m to mm",
    ],
    "solve_pipe_continuity": [
        "A = pi*D^2/4",
        "v = Q/A",
        "Convert Q from L/s to m^3/s and D from mm to m",
    ],
    "solve_darcy_weisbach": [
        "v = Q/A",
        "hf = f*(L/D)*v^2/(2g)",
        "g = 9.80665 m/s^2",
    ],
    "solve_manning_rectangular": [
        "A = b*y",
        "Pwet = b + 2y",
        "R = A/Pwet",
        "V = (1/n)*R^(2/3)*S^(1/2)",
        "Q = A*V",
    ],
    "solve_effective_stress": [
        "sigma_prime_v = sigma_v - u",
    ],
    "solve_consolidation": [
        "sigma_final_prime = sigma_initial_prime + delta_sigma_prime",
        "Sc = Cc*H/(1+e0)*log10(sigma_final_prime/sigma_initial_prime)",
        "Convert settlement from m to mm",
    ],
    "solve_slab_concrete_quantity": [
        "Aplan = L*B",
        "Vconcrete = L*B*t",
    ],
    "solve_rebar_mass": [
        "Abar = pi*d^2/4",
        "mass_per_m = rho*Abar",
        "total_mass = mass_per_m*total_length",
        "rho_steel = 7850 kg/m^3",
    ],
    "solve_gear_ratio": [
        "i = Zdriven/Zdriver",
        "ndriven = ndriver/i",
        "Ideal torque multiplier = i; output direction reverses for one external mesh",
    ],
    "solve_three_phase_power": [
        "S = sqrt(3)*Vline*Iline",
        "P = sqrt(3)*Vline*Iline*power_factor",
    ],
    "solve_leveling": [
        "HI = RLbenchmark + BS",
        "RLnew = HI - FS",
        "Rise/Fall = RLnew - RLbenchmark",
    ],
    "solve_rectangle_section": [
        "A = b*h",
        "Ix = b*h^3/12",
        "Zx = Ix/(h/2)",
    ],
    "solve_earthwork_average_end_area": [
        "Amean = (A1 + A2)/2",
        "V = L*Amean",
    ],
}


def _builder(
    family: str,
    solver: Callable[[dict[str, float]], dict[str, Any]],
    input_factory: Callable[[random.Random], dict[str, float]],
    prompts: tuple[str, ...],
    method: str,
    assumptions: tuple[str, ...],
) -> tuple[Callable[[random.Random], dict[str, Any]], str]:
    equations = GOVERNING_EQUATIONS.get(solver.__name__)
    if not equations:
        raise ValueError(f"No reviewed governing equations registered for {solver.__name__}")

    def make(rng: random.Random) -> dict[str, Any]:
        inputs = input_factory(rng)
        solved = solver(inputs)
        prompt = rng.choice(prompts).format(**inputs)
        expected = {
            "status": "calculated",
            "method": method,
            "governing_equations": equations,
            "inputs": inputs,
            "calculation_results": solved["values"],
            "values": solved["values"],
            "units": solved["units"],
            "assumptions": list(assumptions),
            "limitations": [
                "This is a bounded educational calculation using the stated model.",
                "It is not a full design, statutory approval, site inspection or safety certification.",
                "Check the applicable project standards and independent engineering requirements before real use.",
            ],
        }
        expected["calculation_steps"] = solved.get("steps") or [
            "Read the supplied inputs and keep their units explicit; convert quantities to a consistent unit system where required.",
            "Apply the governing equations in the listed order and retain intermediate values with units.",
            "Check dimensional consistency, sign convention and the physical reasonableness of the calculated outputs.",
        ]
        return {"prompt": prompt, "expected": expected, "solver": solver.__name__}
    return make, solver.__name__


FAMILY_BUILDERS: dict[str, tuple[Callable[[random.Random], dict[str, Any]], str]] = {}


def _register(
    family: str,
    solver: Callable[[dict[str, float]], dict[str, Any]],
    input_factory: Callable[[random.Random], dict[str, float]],
    prompts: tuple[str, ...],
    method: str,
    assumptions: tuple[str, ...],
) -> None:
    FAMILY_BUILDERS[family] = _builder(family, solver, input_factory, prompts, method, assumptions)


def _common_beam(rng: random.Random) -> dict[str, float]:
    return {
        "span_m": _round(rng.uniform(3.0, 12.0), 2),
        "elastic_modulus_GPa": _round(rng.uniform(25.0, 210.0), 2),
        "second_moment_mm4": _round(rng.uniform(1.5e7, 2.5e8), 0),
    }


def _beam_udl_inputs(rng: random.Random) -> dict[str, float]:
    return {**_common_beam(rng), "udl_kN_per_m": _round(rng.uniform(3.0, 45.0), 2)}


def _beam_point_inputs(rng: random.Random) -> dict[str, float]:
    return {**_common_beam(rng), "central_point_load_kN": _round(rng.uniform(10.0, 180.0), 2)}


def _cantilever_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "cantilever_length_m": _round(rng.uniform(1.0, 6.0), 2),
        "tip_load_kN": _round(rng.uniform(2.0, 90.0), 2),
        "elastic_modulus_GPa": _round(rng.uniform(25.0, 210.0), 2),
        "second_moment_mm4": _round(rng.uniform(1.5e7, 2.5e8), 0),
    }


def _axial_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "axial_force_kN": _round(rng.uniform(20.0, 800.0), 2),
        "area_mm2": _round(rng.uniform(500.0, 30000.0), 1),
        "length_m": _round(rng.uniform(0.5, 12.0), 2),
        "elastic_modulus_GPa": _round(rng.uniform(70.0, 210.0), 2),
    }


def _torsion_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "torque_kN_m": _round(rng.uniform(0.2, 8.0), 3),
        "shaft_diameter_mm": _round(rng.uniform(20.0, 140.0), 2),
        "shaft_length_m": _round(rng.uniform(0.2, 4.0), 2),
        "shear_modulus_GPa": _round(rng.uniform(26.0, 82.0), 2),
    }


def _continuity_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "flow_L_per_s": _round(rng.uniform(1.0, 500.0), 3),
        "internal_diameter_mm": _round(rng.uniform(40.0, 800.0), 1),
    }


def _darcy_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "flow_L_per_s": _round(rng.uniform(5.0, 500.0), 3),
        "internal_diameter_mm": _round(rng.uniform(75.0, 800.0), 1),
        "pipe_length_m": _round(rng.uniform(25.0, 2500.0), 1),
        "darcy_friction_factor": _round(rng.uniform(0.012, 0.04), 5),
    }


def _manning_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "channel_width_m": _round(rng.uniform(0.5, 12.0), 2),
        "flow_depth_m": _round(rng.uniform(0.15, 3.0), 2),
        "manning_n": _round(rng.uniform(0.012, 0.035), 5),
        "energy_slope": _round(10 ** rng.uniform(-4.0, -2.0), 6),
    }


def _effective_stress_inputs(rng: random.Random) -> dict[str, float]:
    total = _round(rng.uniform(80.0, 650.0), 2)
    pore = _round(rng.uniform(0.0, min(total * 0.8, 400.0)), 2)
    return {"total_vertical_stress_kPa": total, "pore_water_pressure_kPa": pore}


def _consolidation_inputs(rng: random.Random) -> dict[str, float]:
    initial = _round(rng.uniform(40.0, 350.0), 2)
    increment = _round(rng.uniform(10.0, 250.0), 2)
    return {
        "compression_index_Cc": _round(rng.uniform(0.08, 0.65), 3),
        "compressible_layer_thickness_m": _round(rng.uniform(1.0, 20.0), 2),
        "initial_void_ratio": _round(rng.uniform(0.35, 1.5), 3),
        "initial_effective_stress_kPa": initial,
        "stress_increment_kPa": increment,
    }


def _slab_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "slab_length_m": _round(rng.uniform(3.0, 30.0), 2),
        "slab_width_m": _round(rng.uniform(2.5, 20.0), 2),
        "slab_thickness_m": _round(rng.uniform(0.1, 0.45), 3),
    }


def _rebar_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "bar_diameter_mm": float(rng.choice([8, 10, 12, 16, 20, 25, 32])),
        "total_bar_length_m": _round(rng.uniform(10.0, 12000.0), 3),
    }


def _gear_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "driver_teeth": int(rng.randint(12, 60)),
        "driven_teeth": int(rng.randint(24, 160)),
        "driver_speed_rpm": _round(rng.uniform(100.0, 3600.0), 2),
    }


def _power_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "line_voltage_V": float(rng.choice([380, 400, 415, 440, 480, 690, 3300, 6600, 11000])),
        "line_current_A": _round(rng.uniform(1.0, 600.0), 2),
        "power_factor": _round(rng.uniform(0.72, 0.99), 3),
    }


def _leveling_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "benchmark_reduced_level_m": _round(rng.uniform(10.0, 650.0), 3),
        "backsight_m": _round(rng.uniform(0.5, 4.5), 3),
        "foresight_m": _round(rng.uniform(0.5, 4.5), 3),
    }


def _section_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "breadth_mm": _round(rng.uniform(80.0, 800.0), 1),
        "depth_mm": _round(rng.uniform(120.0, 1500.0), 1),
    }


def _earthwork_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "section_spacing_m": _round(rng.uniform(5.0, 50.0), 2),
        "cut_area_1_m2": _round(rng.uniform(0.5, 80.0), 2),
        "cut_area_2_m2": _round(rng.uniform(0.5, 80.0), 2),
    }


_register(
    "engineering_statics_beam_udl", solve_beam_udl, _beam_udl_inputs,
    (
        "A simply supported prismatic beam spans {span_m} m and carries a full-span UDL of {udl_kN_per_m} kN/m. E is {elastic_modulus_GPa} GPa and I is {second_moment_mm4} mm4. Calculate reactions, maximum sagging moment and maximum deflection.",
        "Check the elastic response of a simply supported beam, span {span_m} m, UDL {udl_kN_per_m} kN/m, E {elastic_modulus_GPa} GPa and I {second_moment_mm4} mm4. Show the unit-consistent results.",
    ),
    "Euler-Bernoulli simply supported beam with full-span uniformly distributed load",
    ("Prismatic linear-elastic beam", "Small deflection Euler-Bernoulli theory", "Full-span UDL and ideal simple supports", "No self-weight or load factors beyond the stated UDL"),
)
_register(
    "engineering_statics_beam_centre_load", solve_beam_centre_load, _beam_point_inputs,
    (
        "A simply supported beam spans {span_m} m with a central point load of {central_point_load_kN} kN. E is {elastic_modulus_GPa} GPa and I is {second_moment_mm4} mm4. Find both reactions, maximum moment and midspan deflection.",
        "For a prismatic simply supported beam (L={span_m} m) with one central point load P={central_point_load_kN} kN, calculate the elastic response using E={elastic_modulus_GPa} GPa and I={second_moment_mm4} mm4.",
    ),
    "Euler-Bernoulli simply supported beam with a central point load",
    ("Prismatic linear-elastic beam", "Small deflection Euler-Bernoulli theory", "Point load is exactly at midspan", "No self-weight or additional loads"),
)
_register(
    "engineering_statics_cantilever_tip_load", solve_cantilever_tip_load, _cantilever_inputs,
    (
        "A cantilever of length {cantilever_length_m} m has a downward tip load of {tip_load_kN} kN. Use E={elastic_modulus_GPa} GPa and I={second_moment_mm4} mm4. Calculate fixed-end actions and tip deflection.",
        "Check a prismatic cantilever: length {cantilever_length_m} m, end load {tip_load_kN} kN, modulus {elastic_modulus_GPa} GPa, second moment {second_moment_mm4} mm4. State shear, moment and tip displacement.",
    ),
    "Euler-Bernoulli cantilever with a point load at the free end",
    ("Prismatic linear-elastic beam", "Small deflection Euler-Bernoulli theory", "Ideal fixed support", "No self-weight or other loads"),
)
_register(
    "engineering_structural_axial_bar", solve_axial_bar, _axial_inputs,
    (
        "A prismatic bar carries an axial tensile force of {axial_force_kN} kN. Its area is {area_mm2} mm2, length {length_m} m and E={elastic_modulus_GPa} GPa. Calculate stress, strain and elongation.",
        "For a straight axial member with P={axial_force_kN} kN, A={area_mm2} mm2, L={length_m} m and E={elastic_modulus_GPa} GPa, find the normal stress, strain and extension.",
    ),
    "Linear-elastic axial deformation of a prismatic bar",
    ("Axial force is concentric", "Uniform cross-section and material", "Small strain linear-elastic response", "No buckling, connection slip or temperature effects"),
)
_register(
    "engineering_mechanical_torsion", solve_solid_shaft_torsion, _torsion_inputs,
    (
        "A solid circular shaft has diameter {shaft_diameter_mm} mm and length {shaft_length_m} m. It transmits {torque_kN_m} kN m. G={shear_modulus_GPa} GPa. Find maximum shear stress and angle of twist.",
        "Calculate elastic torsion for a solid circular shaft: T={torque_kN_m} kN m, d={shaft_diameter_mm} mm, L={shaft_length_m} m and shear modulus G={shear_modulus_GPa} GPa.",
    ),
    "Saint-Venant elastic torsion of a solid circular shaft",
    ("Uniform solid circular shaft", "Linear-elastic isotropic material", "Torque is constant along the shaft", "Stress concentration and fatigue are not included"),
)
_register(
    "engineering_hydraulics_continuity", solve_pipe_continuity, _continuity_inputs,
    (
        "Water flows at {flow_L_per_s} L/s through a full circular pipe with internal diameter {internal_diameter_mm} mm. Find cross-sectional area and mean velocity.",
        "Use continuity Q=AV for a full pipe: discharge {flow_L_per_s} L/s and internal diameter {internal_diameter_mm} mm. Calculate mean velocity.",
    ),
    "Steady incompressible continuity equation Q=AV",
    ("Steady incompressible flow", "Pipe runs full", "Mean velocity based on circular internal area"),
)
_register(
    "engineering_hydraulics_darcy_weisbach", solve_darcy_weisbach, _darcy_inputs,
    (
        "A pipe is {pipe_length_m} m long with internal diameter {internal_diameter_mm} mm. Flow is {flow_L_per_s} L/s and Darcy friction factor is {darcy_friction_factor}. Calculate mean velocity and friction head loss.",
        "For steady pipe flow Q={flow_L_per_s} L/s, D={internal_diameter_mm} mm, L={pipe_length_m} m and Darcy f={darcy_friction_factor}, calculate the Darcy-Weisbach head loss.",
    ),
    "Darcy-Weisbach friction head-loss equation",
    ("Steady incompressible flow", "Constant Darcy friction factor over the pipe", "No minor losses included", "Pipe is full and diameter is constant"),
)
_register(
    "engineering_hydraulics_manning", solve_manning_rectangular, _manning_inputs,
    (
        "A rectangular open channel is {channel_width_m} m wide with flow depth {flow_depth_m} m. Manning n={manning_n} and energy slope={energy_slope}. Calculate area, hydraulic radius, velocity and discharge.",
        "Estimate uniform flow in a rectangular channel using Manning's equation, b={channel_width_m} m, y={flow_depth_m} m, n={manning_n}, S={energy_slope}.",
    ),
    "Manning uniform-flow equation for a rectangular channel",
    ("Steady uniform flow", "Rectangular prismatic channel", "Energy slope equals channel bed slope", "No backwater or rapidly varied flow"),
)
_register(
    "engineering_geotechnical_effective_stress", solve_effective_stress, _effective_stress_inputs,
    (
        "At a soil point the total vertical stress is {total_vertical_stress_kPa} kPa and pore-water pressure is {pore_water_pressure_kPa} kPa. Calculate vertical effective stress.",
        "Apply Terzaghi's effective-stress principle to total vertical stress {total_vertical_stress_kPa} kPa and pore pressure {pore_water_pressure_kPa} kPa.",
    ),
    "Terzaghi effective vertical stress, sigma-prime = total stress minus pore pressure",
    ("The supplied stresses refer to the same point and reference state", "Pore pressure is hydrostatic or is otherwise supplied explicitly"),
)
_register(
    "engineering_geotechnical_consolidation", solve_consolidation, _consolidation_inputs,
    (
        "A normally consolidated clay layer has Cc={compression_index_Cc}, thickness {compressible_layer_thickness_m} m and e0={initial_void_ratio}. Initial effective stress is {initial_effective_stress_kPa} kPa and the increment is {stress_increment_kPa} kPa. Estimate primary settlement.",
        "Using the one-dimensional virgin-compression equation, calculate primary consolidation settlement for H={compressible_layer_thickness_m} m, Cc={compression_index_Cc}, e0={initial_void_ratio}, sigma0-prime={initial_effective_stress_kPa} kPa and delta-sigma-prime={stress_increment_kPa} kPa.",
    ),
    "One-dimensional primary consolidation using the compression-index logarithmic relation",
    ("Normally consolidated soil over the stress increment", "Cc and e0 remain constant through the layer", "Stress increment is uniform through the layer", "Secondary compression and drainage-time rate are not included"),
)
_register(
    "construction_concrete_quantity", solve_slab_concrete_quantity, _slab_inputs,
    (
        "A rectangular slab is {slab_length_m} m by {slab_width_m} m and {slab_thickness_m} m thick. Calculate plan area and theoretical concrete volume.",
        "Take off a plain rectangular slab quantity: L={slab_length_m} m, B={slab_width_m} m and thickness={slab_thickness_m} m. Report area and volume.",
    ),
    "Rectangular slab geometry and volume",
    ("Uniform thickness", "Rectangular plan area", "No openings, waste, camber or overbreak"),
)
_register(
    "construction_reinforcement_mass", solve_rebar_mass, _rebar_inputs,
    (
        "A reinforcement schedule contains {total_bar_length_m} m total length of {bar_diameter_mm} mm diameter steel bar. Using density 7850 kg/m3, estimate mass per metre and total mass.",
        "Estimate the theoretical mass of reinforcement: bar diameter {bar_diameter_mm} mm and combined length {total_bar_length_m} m. Use steel density 7850 kg/m3.",
    ),
    "Steel bar mass from circular cross-sectional area and density",
    ("Solid circular bar", "Steel density is 7850 kg/m3", "No coating, couplers, hooks or cutting waste included"),
)
_register(
    "engineering_mechanical_gear_ratio", solve_gear_ratio, _gear_inputs,
    (
        "A driver gear with {driver_teeth} teeth rotates at {driver_speed_rpm} rpm and meshes with a driven gear with {driven_teeth} teeth. Calculate speed ratio and driven speed.",
        "For an ideal external gear pair with driver Z1={driver_teeth}, driven Z2={driven_teeth}, and input speed {driver_speed_rpm} rpm, find the driven speed and ideal torque multiplier.",
    ),
    "Ideal external spur-gear tooth-count ratio",
    ("One external gear pair", "No slip", "Neglect friction and transmission losses", "Output rotation direction is opposite the driver"),
)
_register(
    "engineering_electrical_three_phase_power", solve_three_phase_power, _power_inputs,
    (
        "A balanced three-phase load operates at line voltage {line_voltage_V} V, line current {line_current_A} A and power factor {power_factor}. Calculate apparent and active power.",
        "For a balanced three-phase system with V-line-line={line_voltage_V} V, line current={line_current_A} A and pf={power_factor}, calculate input kVA and kW.",
    ),
    "Balanced three-phase apparent and active power relation",
    ("Balanced sinusoidal three-phase system", "Line-to-line voltage and line current are supplied", "Power factor is for the complete load", "No harmonic or unbalance correction included"),
)
_register(
    "engineering_surveying_leveling", solve_leveling, _leveling_inputs,
    (
        "A benchmark RL is {benchmark_reduced_level_m} m. The backsight is {backsight_m} m and foresight on the new point is {foresight_m} m. Calculate height of instrument and new reduced level.",
        "Using the height-of-instrument method, benchmark RL={benchmark_reduced_level_m} m, BS={backsight_m} m and FS={foresight_m} m. Find HI, new RL and rise/fall.",
    ),
    "Differential levelling by height-of-instrument method",
    ("Single backsight and single foresight setup", "Staff readings are metres", "No collimation, curvature or refraction correction included"),
)
_register(
    "engineering_structural_section_properties", solve_rectangle_section, _section_inputs,
    (
        "A rectangular section is {breadth_mm} mm wide and {depth_mm} mm deep. Calculate area, second moment of area about the strong axis and elastic section modulus.",
        "For a rectangle b={breadth_mm} mm and h={depth_mm} mm, find A, I about the centroidal strong axis, and Z.",
    ),
    "Centroidal elastic section properties of a solid rectangle",
    ("Homogeneous solid rectangle", "Strong axis is parallel to breadth and perpendicular to depth", "No holes or composite materials"),
)
_register(
    "civil_earthwork_average_end_area", solve_earthwork_average_end_area, _earthwork_inputs,
    (
        "Two consecutive earthwork cross-sections are {section_spacing_m} m apart with cut areas {cut_area_1_m2} m2 and {cut_area_2_m2} m2. Estimate volume using the average-end-area method.",
        "Use the average end area method for section spacing {section_spacing_m} m, area 1 {cut_area_1_m2} m2 and area 2 {cut_area_2_m2} m2. Find the cut volume.",
    ),
    "Average-end-area method for prismoidal earthwork quantities",
    ("Cross-sectional area changes linearly between the two sections", "No bulking/shrinkage factor included", "Both cross-sections use the same datum and units"),
)


def generate_cases(
    *,
    cases_per_domain: int,
    seed: int = 3407,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    if cases_per_domain < 0:
        raise ValueError("cases_per_domain cannot be negative")
    result: dict[str, list[dict[str, Any]]] = {split: [] for split in SPLITS}
    if cases_per_domain == 0:
        return result, {
            "source": SOURCE_NAME,
            "license": SOURCE_LICENSE,
            "cases_per_domain": 0,
            "total_records": 0,
            "split_counts": {split: 0 for split in SPLITS},
            "families": {},
        }
    rng = random.Random(seed)
    family_counts: Counter = Counter()
    solver_names: dict[str, str] = {}
    seen_cases: set[str] = set()

    for family, (make_case, solver_name) in sorted(FAMILY_BUILDERS.items()):
        solver_names[family] = solver_name
        for index in range(cases_per_domain):
            case_id = f"{family}-seed{seed}-{index:07d}"
            if case_id in seen_cases:
                raise ValueError(f"Duplicate generated engineering case ID: {case_id}")
            seen_cases.add(case_id)
            values = make_case(rng)
            expected_text = json.dumps(values["expected"], ensure_ascii=False, sort_keys=True)
            system = (
                "You are NextAI, a careful engineering calculation assistant. "
                "Use only the stated inputs, preserve units, show the governing "
                "relationship, check dimensional consistency, and distinguish "
                "an educational calculation from a complete design or approval."
            )
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": values["prompt"]},
                {"role": "assistant", "content": expected_text},
            ]
            source_group = _sha(f"{family}|{case_id}")
            bucket = int(source_group[:8], 16) % 100
            split = "test" if bucket < 5 else "validation" if bucket < 10 else "train"
            record = {
                "record_id": case_id,
                "domain": family,
                "messages": messages,
                "images": [],
                "source": SOURCE_NAME,
                "license": SOURCE_LICENSE,
                "source_split": "original_synthetic",
                "split": split,
                "source_group_sha256": source_group,
                "split_group": source_group,
                "evidence_level": "L0",
                "native_execution_verified": False,
                "calculation_validation": "deterministic_closed_form_solver",
                "solver": values["solver"],
                "expected": values["expected"],
                "case_family": family,
                "case_index": index,
                "seed": seed,
            }
            result[split].append(record)
            family_counts[family] += 1

    manifest = {
        "schema_version": 1,
        "source": SOURCE_NAME,
        "license": SOURCE_LICENSE,
        "generation_method": "Deterministic analytic engineering cases with unit-aware closed-form solvers",
        "seed": seed,
        "cases_per_domain": cases_per_domain,
        "families": dict(sorted(family_counts.items())),
        "solver_functions": solver_names,
        "split_counts": {split: len(rows) for split, rows in result.items()},
        "total_records": sum(len(rows) for rows in result.values()),
        "split_policy": "Deterministic source-group SHA-256 partition: 90% train, 5% validation, 5% test target; actual counts may differ by hash bucket.",
        "evidence_level": "L0",
        "native_execution_verified": False,
        "limitations": [
            "Analytic cases use the explicit formula and assumptions recorded in every completion.",
            "They do not validate a native CAD/BIM command, project file, code clause or professional design.",
            "No values are generated by copying an external proprietary standard or benchmark solution.",
        ],
    }
    return result, manifest


def write_corpus(
    output_dir: str,
    *,
    cases_per_domain: int,
    seed: int = 3407,
) -> dict[str, Any]:
    from pathlib import Path

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    splits, manifest = generate_cases(cases_per_domain=cases_per_domain, seed=seed)
    for split, rows in splits.items():
        path = output / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--cases-per-domain", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=3407)
    args = parser.parse_args()
    manifest = write_corpus(
        str(args.output_dir),
        cases_per_domain=args.cases_per_domain,
        seed=args.seed,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0



# Additional structural, geotechnical and hydraulic calculation families.
# These are deliberately bounded analytical lessons, not code-compliance checks.
def solve_euler_column_buckling(inputs: dict[str, float]) -> dict[str, Any]:
    length_mm = float(inputs["unsupported_length_m"]) * 1000.0
    factor = float(inputs["effective_length_factor"])
    modulus = float(inputs["elastic_modulus_GPa"]) * 1000.0
    inertia = float(inputs["second_moment_mm4"])
    area = float(inputs["area_mm2"])
    if min(length_mm, factor, modulus, inertia, area) <= 0:
        raise ValueError("Column length, effective-length factor, E, I and area must be positive.")
    effective_length_mm = factor * length_mm
    radius = math.sqrt(inertia / area)
    slenderness = effective_length_mm / radius
    critical_load_n = math.pi**2 * modulus * inertia / effective_length_mm**2
    critical_load_kn = critical_load_n / 1000.0
    critical_stress_mpa = critical_load_n / area
    return {
        "values": {
            "effective_length_mm": _round(effective_length_mm, 6),
            "radius_of_gyration_mm": _round(radius, 6),
            "slenderness_ratio": _round(slenderness, 6),
            "Euler_critical_load_kN": _round(critical_load_kn, 6),
            "Euler_critical_stress_MPa": _round(critical_stress_mpa, 6),
        },
        "units": {
            "effective_length_mm": "mm",
            "radius_of_gyration_mm": "mm",
            "slenderness_ratio": "dimensionless",
            "Euler_critical_load_kN": "kN",
            "Euler_critical_stress_MPa": "MPa",
        },
        "steps": [
            "Convert E from GPa to N/mm² and the unsupported length from m to mm.",
            "Calculate effective length Le = K L and radius of gyration r = sqrt(I/A).",
            "Calculate slenderness Le/r.",
            "Calculate ideal elastic Euler load Pcr = pi² E I / Le², then convert N to kN.",
            "Calculate the corresponding average elastic critical stress Pcr/A.",
        ],
    }


def solve_rankine_active_pressure(inputs: dict[str, float]) -> dict[str, Any]:
    gamma = float(inputs["soil_unit_weight_kN_m3"])
    height = float(inputs["retained_height_m"])
    surcharge = float(inputs["uniform_surcharge_kPa"])
    phi_deg = float(inputs["friction_angle_deg"])
    if gamma <= 0 or height <= 0 or surcharge < 0 or not 0 < phi_deg < 60:
        raise ValueError("Require positive soil weight/height, non-negative surcharge and 0 < phi < 60 degrees.")
    phi = math.radians(phi_deg)
    ka = (1.0 - math.sin(phi)) / (1.0 + math.sin(phi))
    soil_resultant = 0.5 * ka * gamma * height**2
    surcharge_resultant = ka * surcharge * height
    total = soil_resultant + surcharge_resultant
    base_pressure = ka * (gamma * height + surcharge)
    moment_about_base = soil_resultant * height / 3.0 + surcharge_resultant * height / 2.0
    line_of_action = moment_about_base / total if total else 0.0
    return {
        "values": {
            "active_pressure_coefficient_Ka": _round(ka, 8),
            "soil_pressure_resultant_kN_per_m": _round(soil_resultant, 6),
            "surcharge_pressure_resultant_kN_per_m": _round(surcharge_resultant, 6),
            "total_active_resultant_kN_per_m": _round(total, 6),
            "lateral_pressure_at_base_kPa": _round(base_pressure, 6),
            "resultant_height_above_base_m": _round(line_of_action, 6),
        },
        "units": {
            "active_pressure_coefficient_Ka": "dimensionless",
            "soil_pressure_resultant_kN_per_m": "kN/m",
            "surcharge_pressure_resultant_kN_per_m": "kN/m",
            "total_active_resultant_kN_per_m": "kN/m",
            "lateral_pressure_at_base_kPa": "kPa",
            "resultant_height_above_base_m": "m",
        },
        "steps": [
            "Convert the friction angle from degrees to radians.",
            "For level cohesionless backfill, calculate Ka = (1 - sin(phi))/(1 + sin(phi)).",
            "Integrate the triangular soil pressure: Pa,soil = 0.5 Ka gamma H².",
            "Integrate the rectangular surcharge pressure: Pa,q = Ka q H.",
            "Sum the resultants and take moments about the base to locate the combined line of action.",
        ],
    }


def solve_hydrostatic_vertical_gate(inputs: dict[str, float]) -> dict[str, Any]:
    width = float(inputs["gate_width_m"])
    height = float(inputs["gate_height_m"])
    top_depth = float(inputs["gate_top_depth_below_free_surface_m"])
    unit_weight = float(inputs.get("water_unit_weight_kN_m3", 9.81))
    if min(width, height, unit_weight) <= 0 or top_depth < 0:
        raise ValueError("Gate dimensions and water unit weight must be positive; top depth cannot be negative.")
    area = width * height
    centroid_depth = top_depth + height / 2.0
    force = unit_weight * area * centroid_depth
    second_moment = width * height**3 / 12.0
    centre_pressure_depth = centroid_depth + second_moment / (area * centroid_depth)
    return {
        "values": {
            "gate_area_m2": _round(area, 6),
            "centroid_depth_below_free_surface_m": _round(centroid_depth, 6),
            "hydrostatic_resultant_kN": _round(force, 6),
            "second_moment_area_horizontal_centroidal_axis_m4": _round(second_moment, 6),
            "centre_of_pressure_depth_below_free_surface_m": _round(centre_pressure_depth, 6),
            "centre_of_pressure_below_gate_top_m": _round(centre_pressure_depth - top_depth, 6),
        },
        "units": {
            "gate_area_m2": "m²",
            "centroid_depth_below_free_surface_m": "m",
            "hydrostatic_resultant_kN": "kN",
            "second_moment_area_horizontal_centroidal_axis_m4": "m⁴",
            "centre_of_pressure_depth_below_free_surface_m": "m",
            "centre_of_pressure_below_gate_top_m": "m",
        },
        "steps": [
            "Calculate the rectangular gate area A = b h and centroid depth ybar = ytop + h/2.",
            "Calculate the hydrostatic resultant F = gamma_w A ybar.",
            "Calculate the centroidal second moment I_G = b h³/12.",
            "Locate the centre of pressure y_cp = ybar + I_G/(A ybar).",
            "Express the centre-of-pressure position relative to both the free surface and gate top.",
        ],
    }


def solve_terzaghi_strip_footing(inputs: dict[str, float]) -> dict[str, Any]:
    cohesion = float(inputs["effective_cohesion_kPa"])
    surcharge = float(inputs["surcharge_at_foundation_level_kPa"])
    gamma = float(inputs["effective_soil_unit_weight_kN_m3"])
    width = float(inputs["footing_width_m"])
    nc = float(inputs["bearing_factor_Nc"])
    nq = float(inputs["bearing_factor_Nq"])
    ngamma = float(inputs["bearing_factor_Ngamma"])
    factor = float(inputs["factor_of_safety"])
    if cohesion < 0 or surcharge < 0 or min(gamma, width, nc, nq, ngamma) <= 0 or factor <= 1:
        raise ValueError("Require non-negative cohesion/surcharge, positive soil/footing/factors and FS greater than one.")
    cohesion_term = cohesion * nc
    surcharge_term = surcharge * nq
    unit_weight_term = 0.5 * gamma * width * ngamma
    gross_ultimate = cohesion_term + surcharge_term + unit_weight_term
    net_ultimate = gross_ultimate - surcharge
    if net_ultimate <= 0:
        raise ValueError("Calculated net ultimate bearing pressure must be positive.")
    net_allowable = net_ultimate / factor
    gross_allowable = surcharge + net_allowable
    return {
        "values": {
            "cohesion_term_kPa": _round(cohesion_term, 6),
            "surcharge_term_kPa": _round(surcharge_term, 6),
            "unit_weight_term_kPa": _round(unit_weight_term, 6),
            "gross_ultimate_bearing_pressure_kPa": _round(gross_ultimate, 6),
            "net_ultimate_bearing_pressure_kPa": _round(net_ultimate, 6),
            "net_allowable_bearing_pressure_kPa": _round(net_allowable, 6),
            "gross_allowable_bearing_pressure_kPa": _round(gross_allowable, 6),
        },
        "units": {key: "kPa" for key in (
            "cohesion_term_kPa", "surcharge_term_kPa", "unit_weight_term_kPa",
            "gross_ultimate_bearing_pressure_kPa", "net_ultimate_bearing_pressure_kPa",
            "net_allowable_bearing_pressure_kPa", "gross_allowable_bearing_pressure_kPa",
        )},
        "steps": [
            "Use the supplied bearing factors for the selected soil friction angle and Terzaghi convention.",
            "Calculate c Nc, q Nq and 0.5 gamma B Ngamma separately.",
            "Sum the three terms to obtain gross ultimate bearing pressure.",
            "Subtract the existing foundation-level surcharge to obtain net ultimate pressure.",
            "Apply the stated factor of safety to net ultimate pressure, then add surcharge back for gross allowable pressure.",
        ],
    }


def solve_infinite_slope_factor_of_safety(inputs: dict[str, float]) -> dict[str, Any]:
    cohesion = float(inputs["effective_cohesion_kPa"])
    gamma = float(inputs["soil_unit_weight_kN_m3"])
    depth = float(inputs["normal_soil_thickness_m"])
    pore = float(inputs["pore_water_pressure_kPa"])
    beta_deg = float(inputs["slope_angle_deg"])
    phi_deg = float(inputs["effective_friction_angle_deg"])
    if cohesion < 0 or gamma <= 0 or depth <= 0 or pore < 0:
        raise ValueError("Require non-negative cohesion/pore pressure and positive unit weight/thickness.")
    if not 0 < beta_deg < 60 or not 0 <= phi_deg < 60:
        raise ValueError("Require slope angle in (0, 60) degrees and friction angle in [0, 60) degrees.")
    beta = math.radians(beta_deg)
    phi = math.radians(phi_deg)
    total_normal = gamma * depth * math.cos(beta)**2
    effective_normal = total_normal - pore
    driving_shear = gamma * depth * math.sin(beta) * math.cos(beta)
    if effective_normal < 0 or driving_shear <= 0:
        raise ValueError("Pore pressure exceeds total normal stress or driving shear is not positive.")
    available_strength = cohesion + effective_normal * math.tan(phi)
    factor = available_strength / driving_shear
    return {
        "values": {
            "total_normal_stress_kPa": _round(total_normal, 6),
            "effective_normal_stress_kPa": _round(effective_normal, 6),
            "available_shear_strength_kPa": _round(available_strength, 6),
            "driving_shear_stress_kPa": _round(driving_shear, 6),
            "factor_of_safety": _round(factor, 6),
        },
        "units": {
            "total_normal_stress_kPa": "kPa",
            "effective_normal_stress_kPa": "kPa",
            "available_shear_strength_kPa": "kPa",
            "driving_shear_stress_kPa": "kPa",
            "factor_of_safety": "dimensionless",
        },
        "steps": [
            "Convert beta and phi-prime from degrees to radians.",
            "Calculate total normal stress sigma_n = gamma z cos²(beta).",
            "Subtract supplied pore pressure u to obtain effective normal stress.",
            "Calculate available shear strength c-prime + sigma-prime tan(phi-prime).",
            "Calculate driving shear stress gamma z sin(beta) cos(beta) and divide strength by driving stress.",
        ],
    }


GOVERNING_EQUATIONS.update({
    "solve_euler_column_buckling": [
        "Le = K L",
        "r = sqrt(I/A)",
        "lambda = Le/r",
        "Pcr = pi² E I / Le²",
        "sigma_cr = Pcr/A",
        "Use E in N/mm², I in mm⁴, Le and r in mm",
    ],
    "solve_rankine_active_pressure": [
        "Ka = (1 - sin(phi))/(1 + sin(phi))",
        "Pa,soil = 0.5 Ka gamma H²",
        "Pa,q = Ka q H",
        "yR = [Pa,soil(H/3) + Pa,q(H/2)]/[Pa,soil + Pa,q]",
    ],
    "solve_hydrostatic_vertical_gate": [
        "A = b h",
        "ybar = ytop + h/2",
        "F = gamma_w A ybar",
        "I_G = b h³/12",
        "y_cp = ybar + I_G/(A ybar)",
    ],
    "solve_terzaghi_strip_footing": [
        "q_ult,gross = c' Nc + q Nq + 0.5 gamma' B Ngamma",
        "q_ult,net = q_ult,gross - q",
        "q_allow,net = q_ult,net/FS",
        "q_allow,gross = q + q_allow,net",
    ],
    "solve_infinite_slope_factor_of_safety": [
        "sigma_n = gamma z cos²(beta)",
        "sigma'_n = sigma_n - u",
        "tau_f = c' + sigma'_n tan(phi')",
        "tau_d = gamma z sin(beta) cos(beta)",
        "FS = tau_f/tau_d",
    ],
})


def _euler_column_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "unsupported_length_m": _round(rng.uniform(2.0, 10.0), 2),
        "effective_length_factor": _round(rng.uniform(0.5, 2.0), 2),
        "elastic_modulus_GPa": _round(rng.uniform(70.0, 210.0), 2),
        "second_moment_mm4": _round(rng.uniform(2.0e6, 2.0e8), 0),
        "area_mm2": _round(rng.uniform(1200.0, 30000.0), 1),
    }


def _rankine_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "soil_unit_weight_kN_m3": _round(rng.uniform(16.0, 22.0), 2),
        "retained_height_m": _round(rng.uniform(2.0, 10.0), 2),
        "uniform_surcharge_kPa": _round(rng.uniform(0.0, 30.0), 2),
        "friction_angle_deg": _round(rng.uniform(20.0, 40.0), 2),
    }


def _hydrostatic_gate_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "gate_width_m": _round(rng.uniform(0.5, 4.0), 2),
        "gate_height_m": _round(rng.uniform(0.5, 5.0), 2),
        "gate_top_depth_below_free_surface_m": _round(rng.uniform(0.0, 10.0), 2),
        "water_unit_weight_kN_m3": 9.81,
    }


def _terzaghi_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "effective_cohesion_kPa": _round(rng.uniform(0.0, 25.0), 2),
        "surcharge_at_foundation_level_kPa": _round(rng.uniform(0.0, 150.0), 2),
        "effective_soil_unit_weight_kN_m3": _round(rng.uniform(16.0, 22.0), 2),
        "footing_width_m": _round(rng.uniform(1.0, 5.0), 2),
        "bearing_factor_Nc": _round(rng.uniform(10.0, 50.0), 2),
        "bearing_factor_Nq": _round(rng.uniform(5.0, 40.0), 2),
        "bearing_factor_Ngamma": _round(rng.uniform(5.0, 60.0), 2),
        "factor_of_safety": _round(rng.uniform(2.5, 3.5), 2),
    }


def _infinite_slope_inputs(rng: random.Random) -> dict[str, float]:
    beta = _round(rng.uniform(10.0, 35.0), 2)
    gamma = _round(rng.uniform(16.0, 22.0), 2)
    depth = _round(rng.uniform(0.5, 5.0), 2)
    total_normal = gamma * depth * math.cos(math.radians(beta))**2
    return {
        "effective_cohesion_kPa": _round(rng.uniform(0.0, 20.0), 2),
        "soil_unit_weight_kN_m3": gamma,
        "normal_soil_thickness_m": depth,
        "pore_water_pressure_kPa": _round(rng.uniform(0.0, max(0.01, total_normal * 0.65)), 2),
        "slope_angle_deg": beta,
        "effective_friction_angle_deg": _round(rng.uniform(15.0, 35.0), 2),
    }


_register(
    "engineering_structural_euler_column_buckling", solve_euler_column_buckling, _euler_column_inputs,
    (
        "An ideal elastic column has unsupported length {unsupported_length_m} m and effective-length factor K={effective_length_factor}. Its E={elastic_modulus_GPa} GPa, I={second_moment_mm4} mm4 and A={area_mm2} mm2. Calculate slenderness and Euler critical load.",
        "Estimate the elastic Euler buckling load for a prismatic column: L={unsupported_length_m} m, K={effective_length_factor}, E={elastic_modulus_GPa} GPa, I={second_moment_mm4} mm4 and A={area_mm2} mm2.",
    ),
    "Ideal elastic Euler buckling of a prismatic column",
    ("Straight prismatic column with constant E and I", "Effective-length factor represents the selected ideal end restraint model", "Linear-elastic Euler buckling only", "Initial crookedness, residual stress, local buckling, inelasticity and code reduction factors are excluded"),
)
_register(
    "engineering_geotechnical_rankine_active_pressure", solve_rankine_active_pressure, _rankine_inputs,
    (
        "A vertical smooth wall retains level cohesionless backfill of height {retained_height_m} m, unit weight {soil_unit_weight_kN_m3} kN/m3 and friction angle {friction_angle_deg} degrees. A uniform surcharge of {uniform_surcharge_kPa} kPa acts at the surface. Estimate Rankine active thrust per metre run.",
        "For level cohesionless soil behind a vertical smooth wall, H={retained_height_m} m, gamma={soil_unit_weight_kN_m3} kN/m3, phi={friction_angle_deg} degrees and uniform surcharge q={uniform_surcharge_kPa} kPa. Find active resultant and lever arm.",
    ),
    "Rankine active earth pressure for level cohesionless backfill with uniform surcharge",
    ("Vertical smooth wall", "Horizontal level backfill", "Cohesionless drained soil", "No groundwater, wall friction, seismic load, compaction pressure or layered strata"),
)
_register(
    "engineering_hydraulics_hydrostatic_gate", solve_hydrostatic_vertical_gate, _hydrostatic_gate_inputs,
    (
        "A vertical rectangular gate is {gate_width_m} m wide and {gate_height_m} m high. Its top edge is {gate_top_depth_below_free_surface_m} m below the free surface. Using water unit weight {water_unit_weight_kN_m3} kN/m3, calculate hydrostatic force and centre of pressure.",
        "Determine the hydrostatic resultant on a vertical rectangular gate with width {gate_width_m} m, height {gate_height_m} m and top depth {gate_top_depth_below_free_surface_m} m. Use gamma_w={water_unit_weight_kN_m3} kN/m3.",
    ),
    "Hydrostatic resultant and centre of pressure on a vertical plane area",
    ("Static water with a horizontal free surface", "Uniform water unit weight", "Rectangular vertical gate with uniform width", "No dynamic, wave, impact or gate self-weight effects"),
)
_register(
    "engineering_geotechnical_terzaghi_strip_footing", solve_terzaghi_strip_footing, _terzaghi_inputs,
    (
        "A strip footing has width {footing_width_m} m, effective cohesion {effective_cohesion_kPa} kPa, foundation-level surcharge {surcharge_at_foundation_level_kPa} kPa and effective soil unit weight {effective_soil_unit_weight_kN_m3} kN/m3. With supplied Terzaghi factors Nc={bearing_factor_Nc}, Nq={bearing_factor_Nq}, Ngamma={bearing_factor_Ngamma} and FS={factor_of_safety}, estimate gross and net allowable bearing pressures.",
        "Using the supplied Terzaghi bearing factors, calculate strip-footing capacity for B={footing_width_m} m, c'={effective_cohesion_kPa} kPa, q={surcharge_at_foundation_level_kPa} kPa, gamma'={effective_soil_unit_weight_kN_m3} kN/m3, Nc={bearing_factor_Nc}, Nq={bearing_factor_Nq}, Ngamma={bearing_factor_Ngamma} and FS={factor_of_safety}.",
    ),
    "Terzaghi general-shear bearing capacity for a continuous strip footing",
    ("Vertical concentric load on a continuous strip footing", "Level ground and general shear failure", "Bearing factors are supplied for the chosen phi and bearing-capacity convention", "Effective unit weight is supplied after any water-table correction", "No shape, depth, inclination, eccentricity, slope or layered-soil correction"),
)
_register(
    "engineering_geotechnical_infinite_slope", solve_infinite_slope_factor_of_safety, _infinite_slope_inputs,
    (
        "An infinite slope has normal soil thickness {normal_soil_thickness_m} m, unit weight {soil_unit_weight_kN_m3} kN/m3, c'={effective_cohesion_kPa} kPa, pore pressure u={pore_water_pressure_kPa} kPa, slope angle beta={slope_angle_deg} degrees and phi'={effective_friction_angle_deg} degrees. Calculate the simplified factor of safety.",
        "For an infinite slope with beta={slope_angle_deg} degrees, z={normal_soil_thickness_m} m, gamma={soil_unit_weight_kN_m3} kN/m3, c'={effective_cohesion_kPa} kPa, u={pore_water_pressure_kPa} kPa and phi'={effective_friction_angle_deg} degrees, evaluate the planar failure factor of safety.",
    ),
    "Infinite-slope limit-equilibrium factor of safety for a plane parallel to the surface",
    ("Homogeneous infinite slope and planar failure surface", "Normal soil thickness is measured perpendicular to the slope", "Effective-stress Mohr-Coulomb strength with supplied pore pressure", "No finite-slope end effects, transient seepage, tension cracks or seismic load"),
)



def solve_rational_method_runoff(inputs: dict[str, float]) -> dict[str, Any]:
    coefficient = float(inputs["runoff_coefficient"])
    intensity_mm_hr = float(inputs["rainfall_intensity_mm_hr"])
    area_ha = float(inputs["catchment_area_ha"])
    if not 0 < coefficient <= 1 or intensity_mm_hr <= 0 or area_ha <= 0:
        raise ValueError("Require 0 < runoff coefficient <= 1 and positive rainfall intensity and catchment area.")
    intensity_m_s = intensity_mm_hr / 1000.0 / 3600.0
    area_m2 = area_ha * 10000.0
    discharge_m3_s = coefficient * intensity_m_s * area_m2
    return {
        "values": {
            "rainfall_intensity_m_per_s": _round(intensity_m_s, 10),
            "catchment_area_m2": _round(area_m2, 6),
            "peak_runoff_m3_per_s": _round(discharge_m3_s, 8),
            "peak_runoff_L_per_s": _round(discharge_m3_s * 1000.0, 6),
        },
        "units": {
            "rainfall_intensity_m_per_s": "m/s",
            "catchment_area_m2": "m²",
            "peak_runoff_m3_per_s": "m³/s",
            "peak_runoff_L_per_s": "L/s",
        },
        "steps": [
            "Check that the runoff coefficient is dimensionless and lies in (0, 1].",
            "Convert rainfall intensity from mm/h to m/s by dividing by 1000 and 3600.",
            "Convert catchment area from hectares to square metres by multiplying by 10,000.",
            "Apply Q = C i A to obtain peak runoff in m³/s, then convert to L/s.",
            "State that the result is a Rational Method peak estimate, not a runoff hydrograph or storage-routing result.",
        ],
    }


def solve_water_pump_power(inputs: dict[str, float]) -> dict[str, Any]:
    flow_l_s = float(inputs["flow_rate_L_per_s"])
    head = float(inputs["total_dynamic_head_m"])
    pump_efficiency = float(inputs["pump_efficiency"])
    motor_efficiency = float(inputs["motor_efficiency"])
    density = float(inputs.get("water_density_kg_m3", 1000.0))
    if min(flow_l_s, head, density) <= 0:
        raise ValueError("Flow, total dynamic head and fluid density must be positive.")
    if not 0 < pump_efficiency <= 1 or not 0 < motor_efficiency <= 1:
        raise ValueError("Pump and motor efficiencies must lie in (0, 1].")
    flow_m3_s = flow_l_s / 1000.0
    hydraulic_w = density * 9.80665 * flow_m3_s * head
    shaft_w = hydraulic_w / pump_efficiency
    electrical_w = shaft_w / motor_efficiency
    return {
        "values": {
            "flow_rate_m3_per_s": _round(flow_m3_s, 8),
            "hydraulic_power_kW": _round(hydraulic_w / 1000.0, 6),
            "pump_shaft_power_kW": _round(shaft_w / 1000.0, 6),
            "electrical_input_power_kW": _round(electrical_w / 1000.0, 6),
            "combined_pump_motor_efficiency": _round(pump_efficiency * motor_efficiency, 6),
        },
        "units": {
            "flow_rate_m3_per_s": "m³/s",
            "hydraulic_power_kW": "kW",
            "pump_shaft_power_kW": "kW",
            "electrical_input_power_kW": "kW",
            "combined_pump_motor_efficiency": "dimensionless",
        },
        "steps": [
            "Convert flow from L/s to m³/s.",
            "Calculate hydraulic output power Ph = rho g Q H.",
            "Divide hydraulic power by pump efficiency to obtain required shaft power.",
            "Divide shaft power by motor efficiency to estimate electrical input power.",
            "Check that the input power is not below shaft power and shaft power is not below hydraulic output.",
        ],
    }


def solve_elastic_shallow_foundation_settlement(inputs: dict[str, float]) -> dict[str, Any]:
    pressure = float(inputs["net_contact_pressure_kPa"])
    width = float(inputs["footing_width_m"])
    poisson = float(inputs["poisson_ratio"])
    modulus_mpa = float(inputs["soil_elastic_modulus_MPa"])
    influence = float(inputs["settlement_influence_factor"])
    if min(pressure, width, modulus_mpa, influence) <= 0:
        raise ValueError("Net pressure, footing width, soil modulus and influence factor must be positive.")
    if not 0 <= poisson < 0.5:
        raise ValueError("Poisson ratio must lie in [0, 0.5).")
    modulus_kpa = modulus_mpa * 1000.0
    settlement_m = pressure * width * (1.0 - poisson**2) * influence / modulus_kpa
    return {
        "values": {
            "soil_elastic_modulus_kPa": _round(modulus_kpa, 6),
            "elastic_settlement_m": _round(settlement_m, 8),
            "elastic_settlement_mm": _round(settlement_m * 1000.0, 6),
        },
        "units": {
            "soil_elastic_modulus_kPa": "kPa",
            "elastic_settlement_m": "m",
            "elastic_settlement_mm": "mm",
        },
        "steps": [
            "Convert soil elastic modulus from MPa to kPa.",
            "Use the supplied net contact pressure and footing width with s = q B (1 - nu²) Is / Es.",
            "Evaluate the dimensionless Poisson correction and supplied influence factor.",
            "Calculate elastic settlement in metres and convert to millimetres.",
            "Treat this as an immediate elastic estimate only; consolidation, creep, layering and time effects are excluded.",
        ],
    }


GOVERNING_EQUATIONS.update({
    "solve_rational_method_runoff": [
        "i_m/s = i_mm/hr / (1000 * 3600)",
        "A_m² = A_ha * 10000",
        "Q = C i A",
        "Q_L/s = 1000 Q_m³/s",
    ],
    "solve_water_pump_power": [
        "Q_m³/s = Q_L/s / 1000",
        "P_hydraulic = rho g Q H",
        "P_shaft = P_hydraulic / eta_pump",
        "P_electrical = P_shaft / eta_motor",
        "g = 9.80665 m/s²",
    ],
    "solve_elastic_shallow_foundation_settlement": [
        "Es_kPa = Es_MPa * 1000",
        "s = q_net B (1 - nu²) Is / Es",
        "Convert settlement from m to mm",
    ],
})


def _rational_runoff_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "runoff_coefficient": _round(rng.uniform(0.15, 0.95), 3),
        "rainfall_intensity_mm_hr": _round(rng.uniform(15.0, 180.0), 2),
        "catchment_area_ha": _round(rng.uniform(0.5, 80.0), 2),
    }


def _pump_power_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "flow_rate_L_per_s": _round(rng.uniform(0.5, 300.0), 2),
        "total_dynamic_head_m": _round(rng.uniform(5.0, 160.0), 2),
        "pump_efficiency": _round(rng.uniform(0.45, 0.9), 3),
        "motor_efficiency": _round(rng.uniform(0.8, 0.97), 3),
        "water_density_kg_m3": 1000.0,
    }


def _elastic_settlement_inputs(rng: random.Random) -> dict[str, float]:
    return {
        "net_contact_pressure_kPa": _round(rng.uniform(25.0, 300.0), 2),
        "footing_width_m": _round(rng.uniform(1.0, 6.0), 2),
        "poisson_ratio": _round(rng.uniform(0.2, 0.45), 3),
        "soil_elastic_modulus_MPa": _round(rng.uniform(5.0, 80.0), 2),
        "settlement_influence_factor": _round(rng.uniform(0.5, 1.2), 3),
    }


_register(
    "engineering_hydraulics_rational_method_runoff", solve_rational_method_runoff, _rational_runoff_inputs,
    (
        "A catchment of {catchment_area_ha} ha has runoff coefficient C={runoff_coefficient}. For rainfall intensity {rainfall_intensity_mm_hr} mm/h, estimate peak runoff using the Rational Method.",
        "Estimate peak design runoff for area {catchment_area_ha} ha, runoff coefficient {runoff_coefficient} and rainfall intensity {rainfall_intensity_mm_hr} mm/h using Q=C i A.",
    ),
    "Rational Method peak runoff estimate",
    ("Rainfall intensity is uniform over the catchment and duration is appropriate to the time of concentration", "Runoff coefficient represents the selected land-use and antecedent conditions", "Peak discharge only; no hydrograph, detention routing or climate allowance"),
)
_register(
    "engineering_hydraulics_water_pump_power", solve_water_pump_power, _pump_power_inputs,
    (
        "A water pump delivers {flow_rate_L_per_s} L/s against total dynamic head {total_dynamic_head_m} m. Pump efficiency is {pump_efficiency} and motor efficiency is {motor_efficiency}. Calculate hydraulic, shaft and electrical input powers.",
        "Size the ideal power requirement for a water duty Q={flow_rate_L_per_s} L/s and TDH={total_dynamic_head_m} m, with pump efficiency {pump_efficiency} and motor efficiency {motor_efficiency}.",
    ),
    "Steady incompressible pump power from total dynamic head and component efficiencies",
    ("Water density is the stated value", "Flow and total dynamic head are operating-point values", "No starting current, service factor, power-factor or transient design calculation"),
)
_register(
    "engineering_geotechnical_elastic_foundation_settlement", solve_elastic_shallow_foundation_settlement, _elastic_settlement_inputs,
    (
        "A shallow footing has net contact pressure {net_contact_pressure_kPa} kPa and width {footing_width_m} m. Soil Es={soil_elastic_modulus_MPa} MPa, Poisson ratio nu={poisson_ratio} and influence factor Is={settlement_influence_factor}. Estimate immediate elastic settlement.",
        "Estimate immediate elastic settlement for qnet={net_contact_pressure_kPa} kPa, B={footing_width_m} m, Es={soil_elastic_modulus_MPa} MPa, nu={poisson_ratio} and supplied influence factor Is={settlement_influence_factor}.",
    ),
    "Simplified elastic-half-space estimate for shallow footing immediate settlement",
    ("Uniform net contact pressure and homogeneous elastic soil idealisation", "The influence factor is supplied for the footing shape, rigidity and selected settlement convention", "No layer-by-layer modulus profile, consolidation, creep, excavation rebound or time-rate analysis"),
)


if __name__ == "__main__":
    raise SystemExit(main())
