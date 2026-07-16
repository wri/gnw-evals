"""Real-structure agent state fixtures for evaluator tests.

These fixtures are based on actual agent state structures observed from live API
traces. The data values are representative samples matching the real schema.

VERIFIED fixtures (fetched directly from API and confirmed against eval run output):
- BRAZIL_TCL_2020_2023: thread ad54c8ac, run 20260327_093127, INSIGHT-UNIT
  Eval reported: dataset_id=1.0, data_pull=1.0, date=1.0, insight=0.0, canopy=0.0
"""

# ---------------------------------------------------------------------------
# Nigeria agricultural land (INSTRUCT-COMBINE)
# Thread: e3bcd767-e458-4b64-b5ec-78c9e5979870
# dataset_id=1 (Global land cover), chart_type=pie, 8 rows of land cover data
# ---------------------------------------------------------------------------

NIGERIA_AGRICULTURAL_LAND = {
    "user_persona": "Researcher",
    "aoi": {
        "source": "gadm",
        "src_id": "NGA",
        "name": "Nigeria",
        "subtype": "country",
        "gadm_id": "NGA",
    },
    "subregion": None,
    "aoi_name": "Nigeria",
    "subtype": "country",
    "dataset": {
        "dataset_id": 1,
        "dataset_name": "Global land cover",
        "context_layer": None,
    },
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "canopy_density": None,
    "forest_filter": None,
    "statistics": [
        {
            "id": "8f2c1d4e-1a2b-4c3d-9e8f-nigeria-lc24",
            "source_url": "https://analytics.globalnaturewatch.org/v0/land_change/land_cover/analytics/8f2c1d4e",
        },
    ],
    "charts_data": [
        {
            "id": "main_chart",
            "type": "pie",
            "title": "Land Cover in Nigeria (2024)",
            "insight": (
                "In 2024, agricultural land (cropland and cultivated grasslands) constitutes "
                "approximately 41% of Nigeria's total land area. Cropland accounts for "
                "37,168,536 ha and cultivated grasslands for 4,012,000 ha, giving a combined "
                "agricultural total of approximately 41,180,536 ha."
            ),
            "data": [
                {"name": "Cropland", "value": 37168536.0},
                {"name": "Cultivated grassland", "value": 4012000.0},
                {"name": "Forest", "value": 9800000.0},
                {"name": "Shrubland", "value": 12000000.0},
                {"name": "Grassland", "value": 15000000.0},
                {"name": "Wetland", "value": 1200000.0},
                {"name": "Settlement", "value": 3500000.0},
                {"name": "Other", "value": 1000000.0},
            ],
            "xAxis": "name",
            "yAxis": "value",
        },
    ],
    "messages": [],
}

# ---------------------------------------------------------------------------
# Brazil tree cover loss by driver (INSIGHT-INTERP)
# Thread: a915d434-5d80-4199-ab12-8644a662954d
# dataset_id=8 (TCL by driver), chart_type=bar, 8 rows, expected dataset_id=4 → MISMATCH
# ---------------------------------------------------------------------------

BRAZIL_TCL_DRIVERS = {
    "user_persona": "Researcher",
    "aoi": {
        "source": "gadm",
        "src_id": "BRA",
        "name": "Brazil",
        "subtype": "country",
        "gadm_id": "BRA",
    },
    "subregion": None,
    "aoi_name": "Brazil",
    "subtype": "country",
    "dataset": {
        "dataset_id": 8,
        "dataset_name": "Tree cover loss by dominant driver",
        "context_layer": "driver",
    },
    "start_date": "2001-01-01",
    "end_date": "2024-12-31",
    "canopy_density": None,
    "forest_filter": None,
    "statistics": [
        {
            "id": "3b7e9a1c-5d4f-4e2a-8b6c-brazil-drv01",
            "source_url": "https://analytics.globalnaturewatch.org/v0/land_change/tree_cover_loss_by_driver/analytics/3b7e9a1c",
        },
    ],
    "charts_data": [
        {
            "id": "main_chart",
            "type": "bar",
            "title": "Tree Cover Loss by Driver in Brazil (2001-2024)",
            "insight": (
                "Since 2001, Brazil has experienced a loss of over 73 million hectares of tree "
                "cover. The primary driver of this loss is permanent agriculture, accounting for "
                "approximately 45 million hectares (62%). Shifting cultivation contributed "
                "around 12 million hectares (16%). Logging accounted for 8 million hectares "
                "(11%). Wildfire contributed 5 million hectares (7%). Other drivers including "
                "hard commodities, settlements, and natural disturbances make up the remainder."
            ),
            "data": [
                {"name": "Permanent agriculture", "value": 45000000},
                {"name": "Shifting cultivation", "value": 12000000},
                {"name": "Logging", "value": 8000000},
                {"name": "Wildfire", "value": 5000000},
                {"name": "Hard commodities", "value": 1500000},
                {"name": "Settlements & Infrastructure", "value": 900000},
                {"name": "Other natural disturbances", "value": 400000},
                {"name": "Unknown", "value": 200000},
            ],
            "xAxis": "name",
            "yAxis": "value",
        },
    ],
    "messages": [],
}

# ---------------------------------------------------------------------------
# Indonesia TCL in Spanish (LANG)
# Thread: e7aaf334-a847-476d-b70a-433f3f8c448d
# dataset_id=0 (DIST-ALERT), chart_type=line, insight in Spanish, expected dataset_id=4 → MISMATCH
# ---------------------------------------------------------------------------

INDONESIA_SPANISH_TCL = {
    "user_persona": "Researcher",
    "aoi": {
        "source": "gadm",
        "src_id": "IDN",
        "name": "Indonesia",
        "subtype": "country",
        "gadm_id": "IDN",
    },
    "subregion": None,
    "aoi_name": "Indonesia",
    "subtype": "country",
    "dataset": {
        "dataset_id": 0,
        "dataset_name": "Global all ecosystem disturbance alerts (DIST-ALERT)",
        "context_layer": "land_cover",
    },
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "canopy_density": None,
    "forest_filter": None,
    "statistics": [
        {
            "id": "6c1f8d2e-9a3b-4f5c-7d8e-idn-dist2024",
            "source_url": "https://analytics.globalnaturewatch.org/v0/land_change/dist_alerts/analytics/6c1f8d2e",
        },
    ],
    "charts_data": [
        {
            "id": "main_chart",
            "type": "line",
            "title": "Pérdida de cobertura arbórea en Indonesia (2024)",
            "insight": (
                "Según los datos de las Alertas de Perturbación de Ecosistemas Globales "
                "(DIST-ALERT) de 2024, Indonesia experimentó una pérdida significativa de "
                "cobertura arbórea. En total, se registraron alertas en aproximadamente "
                "1.2 millones de hectáreas a lo largo del año, con los picos más altos "
                "observados entre julio y octubre."
            ),
            "data": [
                {"month": "2024-01", "area_ha": 85000},
                {"month": "2024-02", "area_ha": 78000},
                {"month": "2024-03", "area_ha": 92000},
                {"month": "2024-04", "area_ha": 95000},
                {"month": "2024-05", "area_ha": 100000},
                {"month": "2024-06", "area_ha": 110000},
                {"month": "2024-07", "area_ha": 145000},
                {"month": "2024-08", "area_ha": 160000},
                {"month": "2024-09", "area_ha": 155000},
                {"month": "2024-10", "area_ha": 130000},
                {"month": "2024-11", "area_ha": 90000},
                {"month": "2024-12", "area_ha": 80000},
            ],
            "xAxis": "month",
            "yAxis": "area_ha",
        },
    ],
    "messages": [],
}

# ---------------------------------------------------------------------------
# Indonesia TCL with canopy density 50 (PARAM-CANOPY)
# Synthetic state representing correct canopy density parameter applied
# ---------------------------------------------------------------------------

INDONESIA_TCL_CANOPY_50 = {
    "user_persona": "Researcher",
    "aoi": {
        "source": "gadm",
        "src_id": "IDN",
        "name": "Indonesia",
        "subtype": "country",
        "gadm_id": "IDN",
    },
    "subregion": None,
    "aoi_name": "Indonesia",
    "subtype": "country",
    "dataset": {
        "dataset_id": 4,
        "dataset_name": "Tree cover loss",
        "context_layer": None,
    },
    "start_date": "2015-01-01",
    "end_date": "2023-12-31",
    "canopy_density": "50",
    "forest_filter": None,
    "charts_data": [
        {
            "id": "main_chart",
            "type": "bar",
            "title": "Tree Cover Loss in Indonesia (2015-2023, 50% canopy density)",
            "insight": (
                "Using a 50% canopy density threshold, Indonesia lost approximately "
                "3.2 million hectares of tree cover between 2015 and 2023."
            ),
            "data": [
                {"year": y, "area_ha": 350000 + i * 5000}
                for i, y in enumerate(range(2015, 2024))
            ],
            "xAxis": "year",
            "yAxis": "area_ha",
        },
    ],
    "messages": [],
}

# ---------------------------------------------------------------------------
# Indonesia primary forest loss (PARAM-FOREST)
# Synthetic state representing correct forest_filter applied
# ---------------------------------------------------------------------------

INDONESIA_PRIMARY_FOREST = {
    "user_persona": "Researcher",
    "aoi": {
        "source": "gadm",
        "src_id": "IDN",
        "name": "Indonesia",
        "subtype": "country",
        "gadm_id": "IDN",
    },
    "subregion": None,
    "aoi_name": "Indonesia",
    "subtype": "country",
    "dataset": {
        "dataset_id": 4,
        "dataset_name": "Tree cover loss",
        "context_layer": None,
    },
    "start_date": "2015-01-01",
    "end_date": "2023-12-31",
    "canopy_density": "30",
    "forest_filter": "primary_forest",
    "charts_data": [
        {
            "id": "main_chart",
            "type": "bar",
            "title": "Primary Forest Loss in Indonesia (2015-2023)",
            "insight": (
                "Filtered to humid tropical primary forest, Indonesia lost approximately "
                "1.1 million hectares of primary forest between 2015 and 2023."
            ),
            "data": [
                {"year": y, "area_ha": 120000 + i * 2000}
                for i, y in enumerate(range(2015, 2024))
            ],
            "xAxis": "year",
            "yAxis": "area_ha",
        },
    ],
    "messages": [],
}

# ---------------------------------------------------------------------------
# Kalimantan disturbance with driver intersection (PARAM-INTERSECT)
# Synthetic state representing correct context_layer applied
# ---------------------------------------------------------------------------

KALIMANTAN_DRIVER_INTERSECT = {
    "user_persona": "Researcher",
    "aoi": {
        "source": "gadm",
        "src_id": "IDN.6_1",
        "name": "Kalimantan",
        "subtype": "region",
        "gadm_id": "IDN.6_1",
    },
    "subregion": None,
    "aoi_name": "Kalimantan",
    "subtype": "region",
    "dataset": {
        "dataset_id": 0,
        "dataset_name": "Global all ecosystem disturbance alerts (DIST-ALERT)",
        "context_layer": "driver",
    },
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "canopy_density": None,
    "forest_filter": None,
    "charts_data": [
        {
            "id": "main_chart",
            "type": "bar",
            "title": "Disturbance Alerts by Driver in Kalimantan (2024)",
            "insight": (
                "Disturbance alerts in Kalimantan since January 2024, broken down by driver: "
                "agricultural expansion is the dominant driver at 45%, followed by logging at 30%."
            ),
            "data": [
                {"driver": "Agriculture", "alerts": 45000},
                {"driver": "Logging", "alerts": 30000},
                {"driver": "Other", "alerts": 25000},
            ],
            "xAxis": "driver",
            "yAxis": "alerts",
        },
    ],
    "messages": [],
}

# ---------------------------------------------------------------------------
# Empty / failed state (for testing error handling)
# ---------------------------------------------------------------------------

EMPTY_STATE = {
    "user_persona": "Researcher",
    "aoi": None,
    "subregion": None,
    "dataset": None,
    "start_date": None,
    "end_date": None,
    "canopy_density": None,
    "forest_filter": None,
    "charts_data": [],
    "messages": [],
}

# ---------------------------------------------------------------------------
# Brazil TCL 2020-2023 — VERIFIED from live trace
# Thread: ad54c8ac-a6fd-4104-aad8-83a3f7a33fa4 (run 20260327_093127)
# Test group: INSIGHT-UNIT
# Eval run reported: dataset_id=1.0, data_pull=1.0, date=1.0, insight_quality=0.0, canopy=0.0
#
# Key real-state observations:
# - canopy_density=None even though default 30% was used (agent only sets explicitly when overridden)
# - context_layer="Tree cover loss" (the dataset name, NOT a filter)
# - insight reports "2001 to 2024" despite user asking for 2020-2023 → insight_quality=0.0
# ---------------------------------------------------------------------------

BRAZIL_TCL_2020_2023 = {
    "user_persona": "Researcher",
    "aoi": {
        "source": "gadm",
        "src_id": "BRA",
        "name": "Brazil",
        "subtype": "country",
        "gadm_id": "BRA",
    },
    "subregion": None,
    "aoi_name": "Brazil",
    "subtype": "country",
    "dataset": {
        "dataset_id": 4,
        "dataset_name": "Tree cover loss",
        "context_layer": "Tree cover loss",  # dataset name, not a filter
    },
    "start_date": "2020-01-01",
    "end_date": "2023-12-31",
    "canopy_density": None,  # agent does NOT set this for default 30% — only sets when explicitly overridden
    "forest_filter": None,
    "statistics": [
        {
            "id": "ad54c8ac-a6fd-4104-aad8-83a3f7a33fa4",
            "source_url": "https://analytics.globalnaturewatch.org/v0/land_change/tree_cover_loss/analytics/ad54c8ac",
        },
    ],
    "charts_data": [
        {
            "id": "main_chart",
            "type": "bar",
            "title": "Tree Cover Loss in Brazil (2020-2023)",
            "insight": (
                "From 2001 to 2024, Brazil experienced a total tree cover loss of approximately "
                "12.40 million hectares. The primary driver of this loss was permanent agriculture, "
                "accounting for 8.62 million hectares."
            ),
            "data": [
                {"year": 2020, "area_ha": 1540000},
                {"year": 2021, "area_ha": 1380000},
                {"year": 2022, "area_ha": 1120000},
                {"year": 2023, "area_ha": 980000},
                {"year": 2024, "area_ha": 900000},
                {"year": 2019, "area_ha": 1200000},
                {"year": 2018, "area_ha": 1350000},
                {"year": 2017, "area_ha": 1490000},
            ],
            "xAxis": "year",
            "yAxis": "area_ha",
        },
    ],
    "messages": [],
}
