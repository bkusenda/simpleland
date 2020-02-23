class EntityConfig(object):

    def __init__(self):
        """
        NOT IN USE

        """
        self._resting_metabolic_rate = 1.0
        self._consume_rate = 1.0
        self._heal_rate = 1.0

        self._body_durability_factor = 1.0
        self._body_elasticity_factor = 1.0
        self._body_friction_factor = 1.0
        self._vision_distance_factor = 1.0

        # directional (forward,backward,left,right)
        self._move_rate_factor = [1.0, 1.0, 1.0, 1.0]
        self._move_rate_max_factor = [1.0, 1.0, 1.0, 1.0]

        # left, right
        self._rotate_rate_factor = [1.0, 1.0]

        self._fast_twitch_factor = 1.0
        self._lift_capacity_factor = 1.0

        self._strike_speed_factor = 1.0
        self._attach_power_factor = 1.0
        self._attach_distance_factor = 1.0

        self._reaction_delay_factor = 1.0
