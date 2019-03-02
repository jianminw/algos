import gamelib
import random
import math
import warnings
from sys import maxsize
from functools import reduce

"""
Most of the algo code you write will be in this file unless you create new
modules yourself.

Advanced strategy tips: 

Additional functions are made available by importing the AdvancedGameState 
class from gamelib/advanced.py as a replacement for the regular GameState class 
in game.py.

You can analyze action frames by modifying algocore.py.

The GameState.map object can be manually manipulated to create hypothetical 
board states. Though, we recommended making a copy of the map to preserve 
the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        random.seed()

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


    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.AdvancedGameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        #game_state.suppress_warnings(True)  #Uncomment this line to suppress warnings.


        # get information about the board and then employ the strategy
        board_units = self.get_diagnostics(game_state)
        game_state.open_locs = self.undefended_locs(game_state)
        self.strategy(game_state, board_units)

        game_state.submit_turn()

    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """
    def strategy(self, game_state, board_units):
        
        # defend against front-defending peoples
        self.defend_front(game_state, board_units)

        # Build defenses
        self.build_defences(game_state, board_units)

        # Finally deploy our information units to attack.
        self.deploy_attackers(game_state)


    def build_defences(self, game_state, board_units):
        # defend front corners
        self.basic_setup(game_state)

        #  we get all locations on our half of the map in the arena bounds.
        all_locations = []
        for i in range(game_state.ARENA_SIZE):
            for j in range(math.floor(game_state.ARENA_SIZE / 2)):
                if (game_state.game_map.in_arena_bounds([i, j])):
                    all_locations.append([i, j])

        possible_locations = self.filter_blocked_locations(all_locations, game_state)

        # place destructors
        if(len(board_units["D0"]) < 15):
            for _ in range(10):
                # First destructor
                loc = random.randint(0, len(possible_locations) - 1)
                location = possible_locations[loc]
                bad_ranges = [game_state.game_map.get_locations_in_range((elt.x, elt.y), 2)
                              for elt in board_units["D0"]]
                bad_locs = [elt for row in bad_ranges for elt in row]
    
    
                # place the destroyers
                if(game_state.number_affordable(DESTRUCTOR) > 0 and
                   game_state.can_spawn(DESTRUCTOR, location) and
                   location not in bad_locs and location[1] != 10):
                    # add destroyers not too close to each other
                    game_state.attempt_spawn(DESTRUCTOR, location)
                    possible_locations.remove(location)
                    bad_locs.extend(game_state.game_map.get_locations_in_range(location, 2))


        # Then building encryptors
        firewall_locations = [[2 * i, game_state.HALF_ARENA - 2]
                for i in range(game_state.HALF_ARENA)[1:]]

        for i in range(len(firewall_locations)):
            location = firewall_locations[i if i % 2 == 0 else -i]
            if(game_state.number_affordable(ENCRYPTOR) > 0 and
               game_state.can_spawn(ENCRYPTOR, location)):
                game_state.attempt_spawn(ENCRYPTOR, location)

        """
        While we have cores to spend, build a random Encryptor.
        """
        while (game_state.get_resource(game_state.CORES) >= 
               game_state.type_cost(ENCRYPTOR) and 
               len(possible_locations) > 0):

            # Choose a random location.
            location1 = possible_locations[random.randint(0,
                                           len(possible_locations) - 1)]
            location2 = possible_locations[random.randint(0,
                                           len(possible_locations) - 1)]

            build_location = location1 if(location1[0] >=
                                          location2[0]) else location2
            """
            Build it and remove the location since you can't place two 
            firewalls in the same location.
            """
            if(len(board_units["D0"]) + len(board_units["D1"]) > 49):
                break
            game_state.attempt_spawn(ENCRYPTOR, build_location)
            possible_locations.remove(build_location)


    def deploy_attackers(self, game_state):
        deployed = False
        for loc in game_state.open_locs:
            # if on our side, then deploy forces!
            if(loc[1] < game_state.HALF_ARENA):
                self.spawn_list(game_state, EMP, [loc])
                self.spawn_list(game_state, PING, [loc])
                deployed = True

        # if we didn't already deploy an EMP, deploy one at random
        if(not deployed):
            # this helps destroy firewalls and hopefully other units too.
            seed = random.randint(0, 13)
            if(game_state.number_affordable(EMP) > 0 and
                game_state.can_spawn(EMP, [seed, 13 - seed])):
                game_state.attempt_spawn(EMP, [seed, 13 - seed], game_state.number_affordable(EMP))

        """
        Now lets send out 3 Pings to hopefully score, we can spawn multiple 
        information units in the same location.
        """
        if(random.random() <= 0.7): # randomly decide if pings be sent
            for _ in range(5):
                # choose placement and number of pings
                rand = random.randint(game_state.HALF_ARENA,
                                      game_state.ARENA_SIZE - 1)

                num_pings = min(3, game_state.number_affordable(PING))
                if(num_pings > 0 and game_state.can_spawn(PING,[rand,rand - 14],
                                                          num_pings)):
                    game_state.attempt_spawn(PING, [rand, rand - 14], num_pings)
                    break # if success on any of 5 tries, stop


        """
        Lastly lets send out Scramblers to help destroy enemy information units.
        A complex algo would predict where the enemy is going to send units and 
        develop its strategy around that. But this algo is simple so lets just 
        send out scramblers in random locations and hope for the best.

        Firstly information units can only deploy on our edges. So lets get a 
        list of those locations.
        """
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        """
        Remove locations that are blocked by our own firewalls since we can't 
        deploy units there.
        """
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        """
        While we have remaining bits to spend lets send out scramblers randomly.
        """
        while(game_state.number_affordable(SCRAMBLER) > 0 and len(deploy_locations) > 0):
            count = 0
           
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(SCRAMBLER, deploy_location)
            count += 1
            if(count >= 3):
                break # don't need more than 4 random scramblers
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered
    

    #### HELPERS

    def basic_setup(self, game_state):
        corner_defences = [[0,13], [27, 13], [1, 12], [26, 12]]
        self.spawn_list(game_state, DESTRUCTOR, corner_defences)

    # create defence that loads up agains people who try to destroy front defences
    def defend_front(self, game_state, board_units):
        front1 = [(i, 11) for i in range(10)[2:]]
        front2 = [(game_state.ARENA_SIZE - i - 2, 11) for i in range(10)[1:]]

        if(len(board_units["Efront1"]) > 5):
            # build wall to destroy the opponents
            self.spawn_list(game_state, FILTER, front1)

            # wipe out front
            if(game_state.number_affordable(EMP) > 0 and
               game_state.can_spawn(EMP, [3, 10])):
                game_state.attempt_spawn(EMP, [3, 10])

        # do the same for the other half of the game board
        elif(len(board_units["Efront2"]) > 5):
            self.spawn_list(game_state, FILTER, front2)
            if(game_state.number_affordable(EMP) > 0 and
               game_state.can_spawn(EMP, [24, 10])):
                game_state.attempt_spawn(EMP, [24, 10])


    def get_diagnostics(self, game_state):

        # create an iterator to go through the map and store everything you find
        game_state.game_map.__iter__()
        loc = [13, 0]
        unit = game_state.game_map.__getitem__(loc)
        units = {"D0" : [], "E0" : [], "F0" : [], "D1" : [], "E1" : [], "F1" : [],
                "Efront1" : [], "Efront2" : []}

        # get data on all of your squares
        try:
            while(True):
                # get the diagnostics
                for elt in unit:
                    if(elt.unit_type == DESTRUCTOR):
                        unit_type = "D"
                    elif(elt.unit_type == ENCRYPTOR):
                        unit_type = "E"
                    else:
                        unit_type = "F"
                    key = unit_type + str(elt.player_index)

                    if(game_state.HALF_ARENA <= loc[1] and loc[1] < game_state.HALF_ARENA + 2):
                        # put the front two rows into lists based on the side
                        if(loc[0] < game_state.HALF_ARENA):
                            units["Efront1"].append((elt.x, elt.y))
                        else:
                            units["Efront2"].append((elt.x, elt.y))
                
                    # put this unit into the dictionary
                    units[key].append(elt)

                # move on to the next space
                loc = game_state.game_map.__next__()
                unit = game_state.game_map.__getitem__(loc)

        except StopIteration:
            return units

    # build units of type unit in locs L
    def spawn_list(self, game_state, unit, L):
        for loc in L:
            if(game_state.number_affordable(unit) > 0 and
               game_state.can_spawn(unit, loc)):
                game_state.attempt_spawn(unit, loc)


    # gets the undefended locations
    def undefended_locs(self, game_state):
        undef_locs = []
        edges = [game_state.game_map.TOP_RIGHT, game_state.game_map.TOP_LEFT,
                 game_state.game_map.BOTTOM_RIGHT, game_state.game_map.BOTTOM_RIGHT]

        for i, edge in enumerate(game_state.game_map.get_edges()):
            for loc in edge:
                if(game_state.contains_stationary_unit(loc)):
                    continue
                # get path of attackers from each location
                path = game_state.find_path_to_edge(loc, edges[(i + 2) % 4])
                attackers = [attacker for elt in path
                                     for attacker in game_state.get_attackers(elt, 1 - i//2)]
                if len(attackers) == 0:
                    undef_locs.append(loc)

        game_state.warn(str(undef_locs))
        return undef_locs


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
