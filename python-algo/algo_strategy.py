import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global FILTER, ENCRYPTOR, DESTRUCTOR, PING, EMP, SCRAMBLER
        FILTER = config["unitInformation"][0]["shorthand"]
        ENCRYPTOR = config["unitInformation"][1]["shorthand"]
        DESTRUCTOR = config["unitInformation"][2]["shorthand"]
        PING = config["unitInformation"][3]["shorthand"]
        EMP = config["unitInformation"][4]["shorthand"]
        SCRAMBLER = config["unitInformation"][5]["shorthand"]
        # This is a good place to do initial setup
        self.scored_on_locations = []

    
        

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        #game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy_defense(game_state)
        self.attack_strategy(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """


    def starter_strategy(self, game_state):
        game_state.attempt_spawn(EMP, [24, 10], 3)
        """
        For defense we will use a spread out layout and some Scramblers early on.
        We will place destructors near locations the opponent managed to score on.
        For offense we will use long range EMPs if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Pings to try and score quickly.
        """
        # First, place basic defenses
        self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)

        # If the turn is less than 5, stall with Scramblers and wait to see enemy's base
        if game_state.turn_number < 5:
            self.stall_with_scramblers(game_state)
        else:
            # Now let's analyze the enemy base to see where their defenses are concentrated.
            # If they have many units in the front we can build a line for our EMPs to attack them at long range.
            if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
                self.emp_line_strategy(game_state)
            else:
                # They don't have many units in the front so lets figure out their least defended area and send Pings there.

                # Only spawn Ping's every other turn
                # Sending more at once is better since attacks can only hit a single ping at a time
                if game_state.turn_number % 2 == 1:
                    # To simplify we will just check sending them from back left and right
                    ping_spawn_location_options = [[13, 0], [14, 0]]
                    best_location = self.least_damage_spawn_location(game_state, ping_spawn_location_options)
                    game_state.attempt_spawn(PING, best_location, 1000)

                # Lastly, if we have spare cores, let's build some Encryptors to boost our Pings' health.
                encryptor_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
                game_state.attempt_spawn(ENCRYPTOR, encryptor_locations)


# -----------------------------------------------------------------------------------------------------------

    # THIS IS THE MAIN METHOD FOR ALL ATTACKS
    def attack_strategy(self, game_state):
        self.send_in_scramblers(game_state)
        if game_state.get_resource(game_state.BITS) >= 12:
            self.attack_from_top_left(game_state, 12)

    # sends in attack from top left
    def attack_from_top_left(self, game_state, ping_count=1):
        for i in range(ping_count):
            game_state.attempt_spawn(PING, [5, 8])

    # sends in scramblers to dispel opponent's attack
    def send_in_scramblers(self, game_state):
        if game_state.turn_number <= 5:
            return
        enemy_bits = game_state.get_resource(game_state.BITS, 1)
        if enemy_bits <= 8:
            scrambler_count = 0
        elif enemy_bits <= 11:
            scrambler_count = 1
        elif enemy_bits <= 15:
            scrambler_count = 2
        else:
            scrambler_count = 3
        for i in range(scrambler_count):
            if i % 2 == 0:
                game_state.attempt_spawn(SCRAMBLER, [9, 4])
            else:
                game_state.attempt_spawn(SCRAMBLER, [18, 4])


    # experiment
    def starter_strategy_raptor_experiment(self, game_state):
        filter_locations = [[0, 13], [1, 13], [2, 13], [25, 13], [26, 13], [27, 13], [3, 12], [24, 12], [4, 11],
                            [23, 11], [5, 10], [22, 10], [6, 9], [21, 9], [7, 8], [20, 8], [8, 7], [19, 7], [9, 6],
                            [10, 6], [11, 6], [16, 6], [17, 6], [18, 6]]

        encrypter_locations = [[4, 10], [23, 10], [5, 9], [22, 9], [6, 8], [21, 8], [7, 7], [20, 7], [8, 6], [19, 6]]

        if game_state.turn_number <= 2:
             game_state.attempt_spawn(FILTER, filter_locations)
        elif game_state.turn_number < 5:
            game_state.attempt_spawn_limit(DESTRUCTOR, [[24,11]], 1)
            game_state.attempt_spawn_limit(ENCRYPTOR, encrypter_locations, 2)
            game_state.attempt_spawn(FILTER, filter_locations)


    # basic updated raptor strategy
    def raptor_defense(self, game_state):

        filter_locations_urgent = [[0, 13], [1, 13], [2, 13], [25, 13], [26, 13], [27, 13], [3, 12], [24, 12], [4, 11],
                            [23, 11], [5, 10], [22, 10], [6, 9], [21, 9], [7, 8], [20, 8], [8, 7], [19, 7], [9, 6],
                            [10, 6], [11, 6], [16, 6], [17, 6], [18, 6]]

        encrypter_locations = [[4, 10], [23, 10], [5, 9], [22, 9], [6, 8], [21, 8], [7, 7], [20, 7], [8, 6], [19, 6]]

        destructor_locations = [[3, 13], [24, 13], [4, 12], [23, 12], [5, 11], [22, 11], [6, 10],
                                      [21, 10], [7, 9], [20, 9], [8, 8], [19, 8], [9, 7], [10, 7], [11, 7],
                                      [16, 7], [17, 7], [18, 7]]

        # try to respawn these every time - want to replace

        game_state.attempt_spawn(FILTER, filter_locations_urgent)
        game_state.attempt_spawn(ENCRYPTOR, encrypter_locations)
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations)



    # basic updated raptor strategy
    def starter_strategy_defense(self, game_state):

        filter_locations_urgent = [[0, 13], [1, 13], [2, 13], [25, 13], [26, 13], [27, 13], [3, 13], [24, 13]]

        destructor_locations = [[4, 12], [23, 12], [5, 11], [22, 11], [6, 10],
                                      [21, 10], [7, 9], [20, 9], [8, 8], [19, 8], [9, 7], [10, 7], [11, 7],
                                      [16, 7], [17, 7], [18, 7]]

        filter_locations_secondary = [[4, 13], [23, 13], [5, 12], [22, 12], [6, 11], [21, 11], [7, 10], [20, 10],
                                      [8, 9], [19, 9], [9, 8], [18, 8], [10, 7], [17, 7]]

        encrypter_locations = [[24, 12], [4, 11], [23, 11], [5, 10], [22, 10], [6, 9], [21, 9], [7, 8], [20, 8], [8, 7], [19, 7], [9, 6], [18, 6]]


        # try to respawn these every time - want to replace
        game_state.attempt_spawn(FILTER, filter_locations_urgent)
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations)
        game_state.attempt_spawn(FILTER, filter_locations_secondary)


        # extra defense / attack helper
        game_state.attempt_spawn_limit(ENCRYPTOR, encrypter_locations, 2)
        game_state.attempt_spawn(FILTER, filter_locations_secondary)







# -----------------------------------------------------------------------------------------------------------------------

    def replace_v_shape_defense(self, game_state):
        test = 2
        # while cores are above 5 maybe
            # loop through list of filter locations map replacing missing filters

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy EMPs can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place destructors that attack enemy units
        destructor_locations = [[0, 13], [27, 13], [8, 11], [19, 11], [13, 11], [14, 11]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations)
        
        # Place filters in front of destructors to soak up damage for them
        filter_locations = [[8, 12], [19, 12]]
        game_state.attempt_spawn(FILTER, filter_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build destructor one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(DESTRUCTOR, build_location)

    def stall_with_scramblers(self, game_state):
        """
        Send out Scramblers at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own firewalls 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining bits to spend lets send out scramblers randomly.
        while game_state.get_resource(game_state.BITS) >= game_state.type_cost(SCRAMBLER) and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(SCRAMBLER, deploy_location)
            """
            We don't have to remove the location since multiple information 
            units can occupy the same space.
            """

    def emp_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our EMP's can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [FILTER, DESTRUCTOR, ENCRYPTOR]
        cheapest_unit = FILTER
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost < gamelib.GameUnit(cheapest_unit, game_state.config).cost:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our EMPs from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn EMPs next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(EMP, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR, game_state.config).damage
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
