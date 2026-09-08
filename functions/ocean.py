"""Ocean-indicator helpers used by the national biochemistry and DHW notebooks."""

import numpy as np
import pandas as pd
from scipy import stats


def process_trend_with_nan(data):
    """Return change, fitted values, annual rate, mean p-value and rate error.

    The time coordinate may accompany any number of spatial dimensions. Fits
    are calculated independently at every grid cell while ignoring NaNs.
    """
    data = data.transpose("time", ...)
    flat = np.asarray(data, dtype=float).reshape(data.shape[0], -1)
    time = pd.to_datetime(data.time.values)
    time_years = (time - time[0]).days.to_numpy() / 365.25

    fitted = np.full_like(flat, np.nan)
    rates = np.full(flat.shape[1], np.nan)
    errors = np.full(flat.shape[1], np.nan)
    p_values = np.full(flat.shape[1], np.nan)
    for i, values in enumerate(flat.T):
        valid = np.isfinite(values)
        if valid.sum() < 2:
            continue
        result = stats.linregress(time_years[valid], values[valid])
        fitted[:, i] = result.intercept + result.slope * time_years
        rates[i] = result.slope
        errors[i] = result.stderr
        p_values[i] = result.pvalue

    spatial_shape = data.shape[1:]
    fitted = fitted.reshape(data.shape)
    change = (fitted[-1] - fitted[0]).reshape(spatial_shape)
    rate = rates.reshape(spatial_shape)
    error = errors.reshape(spatial_shape)
    return change, fitted, rate, float(np.nanmean(p_values)), float(np.nanmean(error))


def classify_bleaching_level(hotspot, dhw):
    if hotspot <= 0:
        return "No stress"
    if hotspot < 1:
        return "Bleaching Watch"
    if dhw < 4:
        return "Bleaching Warning"
    if dhw < 8:
        return "Alert level 1"
    return "Alert level 2"


def process_bleaching_levels(data_crw):
    """Summarise bleaching-alert days over the first and last ten years."""
    frame = data_crw.copy()
    frame.index = pd.to_datetime(frame.index)
    frame["year"] = frame.index.year
    frame["bleaching_level"] = frame.apply(
        lambda row: classify_bleaching_level(
            row["SSTA@90th_HS"], row["DHW_from_90th_HS>1"]
        ),
        axis=1,
    )
    years = np.sort(frame.year.unique())
    frame["period"] = pd.NA
    frame.loc[frame.year.isin(years[:10]), "period"] = "First 10 years"
    frame.loc[frame.year.isin(years[-10:]), "period"] = "Last 10 years"
    order = [
        "No stress", "Bleaching Watch", "Bleaching Warning",
        "Alert level 1", "Alert level 2",
    ]
    counts = (
        frame.dropna(subset=["period"])
        .groupby(["period", "bleaching_level"])
        .size().rename("n_days").reset_index()
    )
    counts["bleaching_level"] = pd.Categorical(
        counts.bleaching_level, categories=order, ordered=True
    )
    pivot = counts.pivot(
        index="bleaching_level", columns="period", values="n_days"
    ).fillna(0)
    return frame, pivot
