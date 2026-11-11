"""Add status effects for high priority Status.json flags"""
import json
from pathlib import Path

# Read existing effects
with open('config/visual_effects.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# New status effects (priority > 6)
new_effects = [
    {
        'id': 'overheat_warning',
        'name': 'Overheating Warning',
        'description': 'Critical overheat alert - fast red pulse',
        'steps': [{
            'step_id': 'step_0',
            'effect_type': 'breath',
            'params': {
                'colors': [[255, 0, 0], [255, 100, 0]],
                'duration_ms': 800,
                'direction': None, 'speed': None,
                'num_loops': None, 'loop_infinite': True,
                'fade_in_ms': 0,
                'glitch_percentage': None, 'glitch_duration_ms': None,
                'duration_variability': None, 'persistence_percentage': None,
                'color_variation': None, 'intensity': None, 'density': None,
                'wave_weights': None, 'height': None, 'tail_length': None,
                'wave_frequency': None, 'ripple': None, 'bolt_interval_ms': None,
                'falloff': None, 'ring_width': None, 'decay_rate': None
            }
        }],
        'topology_support': ['0D', '1D', '2D'],
        'post_behavior': 'loop'
    },
    {
        'id': 'interdiction_alert',
        'name': 'Interdiction Alert',
        'description': 'Being interdicted - yellow/red glitch',
        'steps': [{
            'step_id': 'step_0',
            'effect_type': 'glitch',
            'params': {
                'colors': [[20, 20, 60], [255, 200, 0], [255, 0, 0], [255, 100, 0]],
                'duration_ms': 3000,
                'direction': None, 'speed': None,
                'num_loops': None, 'loop_infinite': True,
                'fade_in_ms': 0,
                'glitch_percentage': 0.3, 'glitch_duration_ms': 100,
                'duration_variability': 0.6, 'persistence_percentage': 0.2,
                'color_variation': 0.3, 'intensity': None, 'density': None,
                'wave_weights': None, 'height': None, 'tail_length': None,
                'wave_frequency': None, 'ripple': None, 'bolt_interval_ms': None,
                'falloff': None, 'ring_width': None, 'decay_rate': None
            }
        }],
        'topology_support': ['1D', '2D'],
        'post_behavior': 'loop'
    },
    {
        'id': 'danger_alert',
        'name': 'In Danger',
        'description': 'Critical danger state - intense red',
        'steps': [{
            'step_id': 'step_0',
            'effect_type': 'breath',
            'params': {
                'colors': [[200, 0, 0], [255, 20, 0]],
                'duration_ms': 1200,
                'direction': None, 'speed': None,
                'num_loops': None, 'loop_infinite': True,
                'fade_in_ms': 0,
                'glitch_percentage': None, 'glitch_duration_ms': None,
                'duration_variability': None, 'persistence_percentage': None,
                'color_variation': None, 'intensity': None, 'density': None,
                'wave_weights': None, 'height': None, 'tail_length': None,
                'wave_frequency': None, 'ripple': None, 'bolt_interval_ms': None,
                'falloff': None, 'ring_width': None, 'decay_rate': None
            }
        }],
        'topology_support': ['0D', '1D', '2D'],
        'post_behavior': 'loop'
    },
    {
        'id': 'low_fuel_warning',
        'name': 'Low Fuel Warning',
        'description': 'Fuel running low - orange breath',
        'steps': [{
            'step_id': 'step_0',
            'effect_type': 'breath',
            'params': {
                'colors': [[255, 80, 0], [255, 160, 0]],
                'duration_ms': 2000,
                'direction': None, 'speed': None,
                'num_loops': None, 'loop_infinite': True,
                'fade_in_ms': 0,
                'glitch_percentage': None, 'glitch_duration_ms': None,
                'duration_variability': None, 'persistence_percentage': None,
                'color_variation': None, 'intensity': None, 'density': None,
                'wave_weights': None, 'height': None, 'tail_length': None,
                'wave_frequency': None, 'ripple': None, 'bolt_interval_ms': None,
                'falloff': None, 'ring_width': None, 'decay_rate': None
            }
        }],
        'topology_support': ['0D', '1D', '2D'],
        'post_behavior': 'loop'
    },
    {
        'id': 'fsd_charging',
        'name': 'FSD Charging',
        'description': 'FSD charging - blue wave',
        'steps': [{
            'step_id': 'step_0',
            'effect_type': 'wave',
            'params': {
                'colors': [[0, 80, 255], [0, 0, 40]],
                'duration_ms': 3000,
                'direction': 'right', 'speed': 1.2,
                'num_loops': None, 'loop_infinite': True,
                'fade_in_ms': 0,
                'glitch_percentage': None, 'glitch_duration_ms': None,
                'duration_variability': None, 'persistence_percentage': None,
                'color_variation': None, 'intensity': None, 'density': None,
                'wave_weights': None, 'height': None, 'tail_length': None,
                'wave_frequency': None, 'ripple': None, 'bolt_interval_ms': None,
                'falloff': None, 'ring_width': None, 'decay_rate': None
            }
        }],
        'topology_support': ['1D', '2D'],
        'post_behavior': 'loop'
    },
    {
        'id': 'low_oxygen_warning',
        'name': 'Low Oxygen (Odyssey)',
        'description': 'Oxygen critical - cyan pulse',
        'steps': [{
            'step_id': 'step_0',
            'effect_type': 'breath',
            'params': {
                'colors': [[0, 255, 255], [0, 150, 200]],
                'duration_ms': 900,
                'direction': None, 'speed': None,
                'num_loops': None, 'loop_infinite': True,
                'fade_in_ms': 0,
                'glitch_percentage': None, 'glitch_duration_ms': None,
                'duration_variability': None, 'persistence_percentage': None,
                'color_variation': None, 'intensity': None, 'density': None,
                'wave_weights': None, 'height': None, 'tail_length': None,
                'wave_frequency': None, 'ripple': None, 'bolt_interval_ms': None,
                'falloff': None, 'ring_width': None, 'decay_rate': None
            }
        }],
        'topology_support': ['0D', '1D', '2D'],
        'post_behavior': 'loop'
    },
    {
        'id': 'low_health_warning',
        'name': 'Low Health (Odyssey)',
        'description': 'Health critical - dark red pulse',
        'steps': [{
            'step_id': 'step_0',
            'effect_type': 'breath',
            'params': {
                'colors': [[150, 0, 0], [220, 20, 0]],
                'duration_ms': 1000,
                'direction': None, 'speed': None,
                'num_loops': None, 'loop_infinite': True,
                'fade_in_ms': 0,
                'glitch_percentage': None, 'glitch_duration_ms': None,
                'duration_variability': None, 'persistence_percentage': None,
                'color_variation': None, 'intensity': None, 'density': None,
                'wave_weights': None, 'height': None, 'tail_length': None,
                'wave_frequency': None, 'ripple': None, 'bolt_interval_ms': None,
                'falloff': None, 'ring_width': None, 'decay_rate': None
            }
        }],
        'topology_support': ['0D', '1D', '2D'],
        'post_behavior': 'loop'
    },
    {
        'id': 'extreme_heat',
        'name': 'Extreme Heat (Odyssey)',
        'description': 'Extreme heat environment - fire effect',
        'steps': [{
            'step_id': 'step_0',
            'effect_type': 'fire',
            'params': {
                'colors': [[200, 30, 0], [255, 220, 0]],
                'duration_ms': 5000,
                'direction': None, 'speed': None,
                'num_loops': None, 'loop_infinite': True,
                'fade_in_ms': 0,
                'glitch_percentage': None, 'glitch_duration_ms': None,
                'duration_variability': None, 'persistence_percentage': None,
                'color_variation': None, 'intensity': 0.85, 'density': None,
                'wave_weights': None, 'height': None, 'tail_length': None,
                'wave_frequency': None, 'ripple': None, 'bolt_interval_ms': None,
                'falloff': None, 'ring_width': None, 'decay_rate': None
            }
        }],
        'topology_support': ['2D'],
        'post_behavior': 'loop'
    },
    {
        'id': 'extreme_cold',
        'name': 'Extreme Cold (Odyssey)',
        'description': 'Extreme cold environment - cyan/white shimmer',
        'steps': [{
            'step_id': 'step_0',
            'effect_type': 'breath',
            'params': {
                'colors': [[0, 180, 255], [180, 220, 255]],
                'duration_ms': 1800,
                'direction': None, 'speed': None,
                'num_loops': None, 'loop_infinite': True,
                'fade_in_ms': 0,
                'glitch_percentage': None, 'glitch_duration_ms': None,
                'duration_variability': None, 'persistence_percentage': None,
                'color_variation': None, 'intensity': None, 'density': None,
                'wave_weights': None, 'height': None, 'tail_length': None,
                'wave_frequency': None, 'ripple': None, 'bolt_interval_ms': None,
                'falloff': None, 'ring_width': None, 'decay_rate': None
            }
        }],
        'topology_support': ['0D', '1D', '2D'],
        'post_behavior': 'loop'
    }
]

# Add to effects list
data['effects'].extend(new_effects)

# Write back
with open('config/visual_effects.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f'[OK] Added {len(new_effects)} status effects')
print('Effects created:')
for e in new_effects:
    print(f"  - {e['id']}: {e['name']}")
