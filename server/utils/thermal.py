"""
Thermal sensor mappings and utilities.
"""

# Thermal zone type-to-display-name mapping for readable labels
THERMAL_NAME_MAP: dict[str, str] = {
    "aoss_thermal": "AOSS (Always-On Sensor)",
    "aoss-thermal": "AOSS (Always-On Sensor)",
    "cpuss0_thermal": "CPU SS0 (Gold/Big)",
    "cpuss0-thermal": "CPU SS0 (Gold/Big)",
    "cpuss1_thermal": "CPU SS1 (LITTLE)",
    "cpuss1-thermal": "CPU SS1 (LITTLE)",
    "cpu0_thermal": "CPU0 (Gold)",
    "cpu0-thermal": "CPU0 (Gold)",
    "cpu1_thermal": "CPU1 (Gold)",
    "cpu1-thermal": "CPU1 (Gold)",
    "cpu2_thermal": "CPU2 (LITTLE)",
    "cpu2-thermal": "CPU2 (LITTLE)",
    "cpu3_thermal": "CPU3 (LITTLE)",
    "cpu3-thermal": "CPU3 (LITTLE)",
    "pwr_cluster_thermal": "Power Cluster",
    "pwr-cluster-thermal": "Power Cluster",
    "gpu_thermal": "GPU (Adreno)",
    "gpu-thermal": "GPU (Adreno)",
    "qcom_battery": "Battery",
    "qcom-battery": "Battery",
    "pm660_thermal": "PM660 (PMIC)",
    "pm660-thermal": "PM660 (PMIC)",
    "pm660l_thermal": "PM660L (PMIC)",
    "pm660l-thermal": "PM660L (PMIC)",
}
