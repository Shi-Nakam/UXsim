# Generate a fixed vehicle list CSV for order-exchange intersection research.
#
# Run from the repository root:
#   python generate_vehicle_list_for_order_exchange.py

import csv

import numpy as np


def generate_vehicle_list(
    seed=0,
    t_start=0,
    t_end=120,
    arrival_rate=0.4,
    od_pairs=None,
    od_probabilities=None,
    vot_true_mean=1.0,
    vot_true_std=3.0,
    declared_vot_mode="truthful",
    participation_rate=1.0,
    output_csv="vehicle_list_seed0.csv",
):
    """
    Generate a fixed vehicle list with random departure times, OD pairs, and VOT values.

    Parameters
    ----------
    seed : int
        Random seed for reproducibility.
    t_start, t_end : float
        Departure time window in seconds (inclusive upper bound for generated departures).
    arrival_rate : float
        Vehicle arrival rate in vehicles per second.
    od_pairs : list of tuple[str, str] or None
        Origin-destination pairs. Default: [("orig1", "dest"), ("orig2", "dest")].
    od_probabilities : list of float or None
        Sampling probabilities for od_pairs (must sum to 1). Default: [0.5, 0.5].
    vot_true_mean, vot_true_std : float
        Target mean and standard deviation of vot_true (lognormal distribution).
    declared_vot_mode : str
        How vot_declared is set. Currently only "truthful" is supported.
    participation_rate : float
        Probability that participates_in_order_exchange is True.
    output_csv : str
        Output CSV file path.

    Returns
    -------
    list[dict]
        Generated vehicle records.
    """
    if od_pairs is None:
        od_pairs = [("orig1", "dest"), ("orig2", "dest")]
    if od_probabilities is None:
        od_probabilities = [0.5, 0.5]

    if len(od_pairs) == 0:
        raise ValueError("od_pairs must not be empty.")

    if len(od_pairs) != len(od_probabilities):
        raise ValueError(
            "od_pairs and od_probabilities must have the same length. "
            f"Got {len(od_pairs)} and {len(od_probabilities)}."
        )

    if any(p < 0 for p in od_probabilities):
        raise ValueError("od_probabilities must not contain negative values.")

    if not np.isclose(sum(od_probabilities), 1.0):
        raise ValueError("od_probabilities must sum to 1.")

    if not (0 <= participation_rate <= 1):
        raise ValueError("participation_rate must be between 0 and 1.")

    if vot_true_mean <= 0:
        raise ValueError("vot_true_mean must be positive.")

    if vot_true_std < 0:
        raise ValueError("vot_true_std must be non-negative.")

    if arrival_rate <= 0:
        raise ValueError("arrival_rate must be positive.")

    rng = np.random.default_rng(seed)

    # Log-normal parameters from target mean m and std s:
    # If X ~ LogNormal(mu, sigma), then E[X]=m and Std[X]=s imply
    #   sigma^2 = ln(1 + (s/m)^2)
    #   mu = ln(m) - sigma^2 / 2
    m = vot_true_mean
    s = vot_true_std
    sigma = np.sqrt(np.log(1 + (s / m) ** 2))
    mu = np.log(m) - sigma**2 / 2

    mean_interarrival = 1.0 / arrival_rate
    vehicles = []
    departure_time = t_start
    vehicle_index = 0

    while True:
        interarrival = rng.exponential(scale=mean_interarrival)
        departure_time += interarrival
        if departure_time > t_end:
            break

        od_index = rng.choice(len(od_pairs), p=od_probabilities)
        orig, dest = od_pairs[od_index]

        vot_true = float(rng.lognormal(mean=mu, sigma=sigma))
        participates = bool(rng.random() < participation_rate)

        if participates:
            if declared_vot_mode == "truthful":
                vot_declared = vot_true
            else:
                raise NotImplementedError(
                    f"declared_vot_mode={declared_vot_mode!r} is not implemented."
                )
        else:
            vot_declared = None

        vehicle_index += 1
        vehicles.append(
            {
                "vehicle_id": f"veh_{vehicle_index:06d}",
                "orig": orig,
                "dest": dest,
                "departure_time": departure_time,
                "vot_true": vot_true,
                "vot_declared": vot_declared,
                "participates_in_order_exchange": participates,
            }
        )

    fieldnames = [
        "vehicle_id",
        "orig",
        "dest",
        "departure_time",
        "vot_true",
        "vot_declared",
        "participates_in_order_exchange",
    ]
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for vehicle in vehicles:
            row = vehicle.copy()
            if row["vot_declared"] is None:
                row["vot_declared"] = ""
            row["participates_in_order_exchange"] = str(
                row["participates_in_order_exchange"]
            )
            writer.writerow(row)

    return vehicles


def load_vehicle_list_to_world(W, csv_path):
    """
    Load vehicles from a CSV file into a UXsim World.

    Parameters
    ----------
    W : World
        UXsim World object.
    csv_path : str | Path
        Path to the vehicle list CSV file.

    Returns
    -------
    list[dict]
        CSV rows read by csv.DictReader.
    """
    rows = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            vehicle_id = row["vehicle_id"]
            orig = row["orig"]
            dest = row["dest"]
            departure_time = float(row["departure_time"])
            vot_true = float(row["vot_true"])
            vot_declared = float(row["vot_declared"]) if row["vot_declared"] != "" else None
            participates_in_order_exchange = row["participates_in_order_exchange"] == "True"

            W.addVehicle(
                orig,
                dest,
                departure_time,
                name=vehicle_id,
                vot_true=vot_true,
                vot_declared=vot_declared,
                participates_in_order_exchange=participates_in_order_exchange,
                payment_paid=0,
                payment_received=0,
            )
            rows.append(row)

    return rows


if __name__ == "__main__":
    vehicles = generate_vehicle_list(
        seed=0,
        t_start=0,
        t_end=120,
        arrival_rate=0.4,
        od_pairs=[("orig1", "dest"), ("orig2", "dest")],
        od_probabilities=[0.5, 0.5],
        vot_true_mean=1.0,
        vot_true_std=3.0,
        declared_vot_mode="truthful",
        participation_rate=1.0,
        output_csv="vehicle_list_seed0.csv",
    )

    output_csv = "vehicle_list_seed0.csv"
    print(f"Generated vehicles: {len(vehicles)}")
    print(f"Saved to: {output_csv}")
    print("First 5 rows:")
    for vehicle in vehicles[:5]:
        print(vehicle)
