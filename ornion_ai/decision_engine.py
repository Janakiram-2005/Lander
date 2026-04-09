def calculate_stability(gear):
    heights = [g["height_cm"] for g in gear.values()]
    variance = max(heights) - min(heights)
    if variance < 2: return "A+ (PERFECT)"
    if variance < 5: return "B (ADAPTIVE)"
    return "C (EXTREME)"

def ornion_decide(leg_features, emergency_mode=False):
    gear = {}
    overall_status = "SAFE"
    
    BASE_HEIGHT = 15 if not emergency_mode else 25 # Higher clearance in emergency
    MAX_ADJUSTMENT = 15 if not emergency_mode else 10 # Total max 35cm

    for leg, f in leg_features.items():
        # Calculate landing leg extension
        sensitivity = 25 if not emergency_mode else 35
        slope_adj = f["slope_index"] * sensitivity
        brightness_adj = max(0, (210 - f["mean_brightness"]) / 8)
        hazard_adj = f["hazard_density"] * 15

        total_height = BASE_HEIGHT + slope_adj + brightness_adj + hazard_adj
        total_height = min(total_height, BASE_HEIGHT + MAX_ADJUSTMENT)

        # Emergency "Spread" Logic
        spread_angle = 0
        if emergency_mode:
            # Spread according to local slope and hazard density
            spread_angle = 10 + (f["slope_index"] * 40) + (f["hazard_density"] * 30)
            spread_angle = min(40, spread_angle) # Max 40 degree spread

        leg_status = "SAFE"
        if f["slope_index"] > 0.3 or f["hazard_density"] > 0.25:
            leg_status = "DANGEROUS"
            overall_status = "DANGEROUS"
        elif f["slope_index"] > 0.15 or f["hazard_density"] > 0.12:
            leg_status = "RISKY"
            if overall_status != "DANGEROUS":
                overall_status = "RISKY"

        gear[leg] = {
            "height_cm": round(total_height, 2),
            "spread_angle": round(spread_angle, 1),
            "status": leg_status,
            "raw_features": f
        }

    # Holistic Diagnostics
    hazard_scores = [f["slope_index"] + f["hazard_density"] for f in leg_features.values()]
    worst_hazard = max(hazard_scores)
    hazard_percentage = min(100, int(worst_hazard * 200))

    stability = calculate_stability(gear)
    if emergency_mode:
        stability = "S+ (MAX STABILITY)"
    
    recommendation = "PROCEED WITH LANDING"
    if emergency_mode:
        recommendation = "EMERGENCY PROTOCOL ACTIVE - STABILIZING"
    elif overall_status == "RISKY":
        recommendation = "ENGAGE THRUSTERS - CAUTION"
    elif overall_status == "DANGEROUS":
        recommendation = "ABORT LANDING - SEARCHING ALTERNATE SITE"

    return {
        "gear": gear,
        "overall": {
            "status": overall_status if not emergency_mode else "STABILIZING",
            "hazard_level": f"{hazard_percentage}%",
            "stability": stability,
            "recommendation": recommendation,
            "leg_count": 4,
            "emergency_active": emergency_mode
        }
    }
