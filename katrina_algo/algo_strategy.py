import gamelib
import random
import math
import warnings
from sys import maxsize

"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

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

        self.pathfinder = gamelib.navigation.ShortestPathFinder()

        self.set_constraints()

    def set_constraints(self):
        self.frontline_enemy_threshhold = 7
        self.ping_deployment_threshhold = 7
        self.filter_wall_threshhold = 7
        self.attacker_spawn_near = [3, 10]
        self.attacker_spawn_far = [24, 10]



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
        #game_state.suppress_warnings(True)  #Uncomment this line to suppress warnings.

        self.get_diagnostics(game_state)

        self.pathfinder.initialize_map(game_state)

        self.starter_strategy(game_state)

        game_state.submit_turn()

    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """
    def starter_strategy(self, game_state):

        """
        Then build additional defenses.
        """
        self.new_defences(game_state)

        """
        Finally deploy our information units to attack.
        """
        self.filter_front(game_state)
        self.new_attackers(game_state)


    def filter_front(self, game_state):
        front1 = [(i, 13) for i in range(10)[2:]]
        front2 = [(game_state.ARENA_SIZE - i - 2, 13) for i in range(10)[1:]]
        for location in (front1+front2):
            if game_state.can_spawn(FILTER, location):
                game_state.attempt_spawn(FILTER, location)

    def new_defences(self, game_state):
        firewall_locations = [[0, 13], [1, 12],[26, 12], [27, 13]]
        for location in firewall_locations:
            if game_state.can_spawn(FILTER, location):
                game_state.attempt_spawn(FILTER, location)

        firewall_locations = [[0, 13], [1, 12],[26, 12], [27, 13],
                             [2, 11], [6, 11], [10, 11],
                              [18, 11], [22, 11], [25, 11]]

        for location in firewall_locations:
            if game_state.can_spawn(DESTRUCTOR, location):
                game_state.attempt_spawn(DESTRUCTOR, location)

        for j in range(3, 24):
            location = [j, 11]
            if game_state.can_spawn(FILTER, location):
                game_state.attempt_spawn(FILTER, location)

    def new_attackers(self, game_state):
        #check for which side is open, and deploy on other side?
        frontline_size = len(game_state.board_units["Efront1"]) + len(game_state.board_units["Efront2"])
        enemy_defenses = frontline_size
        enemy_defenses += len(game_state.board_units["Efront3"])
        enemy_defenses += len(game_state.board_units["Efront4"])
        filter_wall = len(game_state.board_units["fline"])
        if frontline_size > self.frontline_enemy_threshhold:
            game_state.attempt_spawn(EMP, self.attacker_spawn_far, game_state.number_affordable(EMP))
        elif enemy_defenses < self.ping_deployment_threshhold:
            game_state.attempt_spawn(PING, self.attacker_spawn_far, game_state.number_affordable(PING))
        elif filter_wall > self.filter_wall_threshhold:
            game_state.attempt_spawn(EMP, self.attacker_spawn_near, game_state.number_affordable(EMP))
        else:
            friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
            available_spawns = self.filter_blocked_locations(friendly_edges, game_state)
            spawn = self.rank_spawns(available_spawns, game_state)
            if spawn != None:
                game_state.attempt_spawn(PING, spawn, game_state.number_affordable(PING))
        # When should we get scramblers?

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def rank_spawns(self, available_spawns, game_state):
        current_best_spawn = None
        current_lowest_damage = -1
        if len(available_spawns) > 0:
            for spawn_point in available_spawns:
                damage = self.damage_taken(spawn_point, game_state)
                if current_best_spawn == None or (damage != None and current_lowest_damage > damage):
                    current_best_spawn = spawn_point
                    current_lowest_damage = damage
            return current_best_spawn
        return None

    def damage_taken(self, spawn_point, game_state):
        spawn_edge = []
        if spawn_point in game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT):
            spawn_edge = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT)
        elif spawn_edge in game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT):
            spawn_edge = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        if len(spawn_edge) > 0:
            targets = []
            for point in spawn_edge:
                targets.append( [27-point[0], 27-point[1]])
            path = self.pathfinder.navigate_multiple_endpoints(spawn_point, targets, game_state)    
            totalDamage = 0
            for l in path:
                for enemy_unit in game_state.get_attackers(l, 0):
                    totalDamage += enemy_unit.damage
            return totalDamage


    ####### Begin Bryce's functions ########

    def get_diagnostics(self, game_state):

        # create an iterator to go through the map and store everything you find
        game_state.game_map.__iter__()
        loc = [13, 0]
        unit = game_state.game_map.__getitem__(loc)
        units = {"D0" : [], "E0" : [], "F0" : [], "D1" : [], "E1" : [], "F1" : [],
                "Efront1" : [], "Efront2" : [], "Efront3" : [], "Efront4" : [],
                "fline" : []}

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

                    if(game_state.HALF_ARENA - 1 <= loc[1] and loc[1] < game_state.HALF_ARENA + 4):
                        # put the front two rows into lists based on the side
                        if(loc[1] == game_state.HALF_ARENA - 1):
                            units["fline"].append([elt.x, elt.y])
                        elif(loc[1] == game_state.HALF_ARENA):
                            units["Efront1"].append([elt.x, elt.y])
                        elif(loc[1] == game_state.HALF_ARENA + 1):
                            units["Efront2"].append([elt.x, elt.y])
                        elif(loc[1] == game_state.HALF_ARENA + 2):
                            units["Efront3"].append([elt.x, elt.y])
                        else:
                            units["Efront4"].append([elt.x, elt.y])


                    # put this unit into the dictionary
                    units[key].append(elt)

                # move on to the next space
                loc = game_state.game_map.__next__()
                unit = game_state.game_map.__getitem__(loc)

        except StopIteration:
            game_state.board_units = units

    # return list of encryptor locations
    def get_encrypt_locs(self, game_state):
        locs = []
        for i in range(24):
            if(i < 4):
                continue
            elif(i % 2 == 0 and game_state.can_spawn(ENCRYPTOR, (i, 9))):
                locs += [(i, 9)]
            elif(game_state.can_spawn(ENCRYPTOR, (25 - i//2, 9))):
                locs += [(25 - i//2, 9)]

        return locs

    # switch attacking sides
    def switch_sides(self, game_state, board_units):
        exit1 = (2, 11)
        exit2 = (25, 11)
        exit3 = (3, 11)
        exit4 = (24, 11)

        for elt in board_units["F"]:
            if(elt.x == exit1[0] and elt.y == exit1[1]):
                game_state.attempt_remove(exit1)
                game_state.attempt_spawn(FILTER, (27 - exit1[0], exit1[1]))
                break

            elif(elt.x == exit2[0] and elt.y == exit2[1]):
                game_state.attempt_remove(exit2)
                game_state.attempt_spawn(FILTER, (27 - exit2[0], exit2[1]))
                break

            elif(elt.x == exit3[0] and elt.y == exit3[1]):
                game_state.attempt_remove(exit3)
                game_state.attempt_spawn(FILTER, (27 - exit3[0], exit3[1]))
                break

            elif(elt.x == exit4[0] and elt.y == exit4[1]):
                game_state.attempt_remove(exit4)
                game_state.attempt_spawn(FILTER, (27 - exit4[0], exit4[1]))
                break

        temp = self.attacker_spawn_near
        self.attacker_spawn_near = self.attacker_spawn_far
        self.attacker_spawn_far = temp


    ##### END BRYCE'S FUCNTIONS #####

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
