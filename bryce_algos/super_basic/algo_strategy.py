import gamelib
import random
import math
import warnings
from sys import maxsize

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
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        #game_state.suppress_warnings(True)  #Uncomment this line to suppress warnings.


        # get information about the board and then employ the strategy
        self.get_diagnostics(game_state)
        self.strategy(game_state)

        game_state.submit_turn()

    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """
    def strategy(self, game_state):
        
        """
        Build defenses.
        """
        self.build_defences(game_state)

        """
        Finally deploy our information units to attack.
        """
        self.deploy_attackers(game_state)


    def build_defences(self, game_state):
        # First destructors
        firewall_locations = [[2 * i + 1, game_state.HALF_ARENA - 2]
                                for i in range(game_state.HALF_ARENA - 1)]
        num_locations = len(firewall_locations)

        for i in range(num_locations):
            # alternate between left and right sides
            location = firewall_locations[i//2] if (i % 2 == 0
                       ) else firewall_locations[num_locations - (i//2) - 1]

            # place the destroyers
            if(game_state.number_affordable(DESTRUCTOR) > 0 and
               game_state.can_spawn(DESTRUCTOR, location)):
                game_state.attempt_spawn(DESTRUCTOR, location)


        # Then building encryptors
        firewall_locations = [[2 * i, game_state.HALF_ARENA - 4]
                for i in range(game_state.HALF_ARENA)[2:-2]]

        for location in firewall_locations:
            if(game_state.number_affordable(ENCRYPTOR) > 0 and
               game_state.can_spawn(ENCRYPTOR, location)):
                game_state.attempt_spawn(ENCRYPTOR, location)

        """
        Lastly lets build encryptors in random locations. Normally building 
        randomly is a bad idea but we'll leave it to you to figure out better 
        strategies. 

        First we get all locations on the bottom half of the map
        that are in the arena bounds.
        """
        all_locations = []
        for i in range(game_state.ARENA_SIZE):
            for j in range(math.floor(game_state.ARENA_SIZE / 2)):
                if (game_state.game_map.in_arena_bounds([i, j])):
                    all_locations.append([i, j])
        
        """
        Then we remove locations already occupied.
        """
        possible_locations = self.filter_blocked_locations(all_locations, game_state)

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
            if(random.random() > 0.7) :
                # we don't ust want encryptors elsewhere
                game_state.attempt_spawn(DESTRUCTOR, build_location)
                possible_locations.remove(build_location)
            elif(random.random() < 0.8) :
                game_state.attempt_spawn(ENCRYPTOR, build_location)
                possible_locations.remove(build_location)


    def deploy_attackers(self, game_state):
        """
        First lets deploy an EMP long range unit to destroy firewalls for us.
        """
        for _ in range(13):
            rand = random.randint(0, 13)
            if(game_state.number_affordable(EMP) > 0 and
               game_state.can_spawn(EMP, [rand, 13 - rand])):
                   game_state.attempt_spawn(EMP, [rand, 13 - rand])
                   break

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
        while(game_state.get_resource(game_state.BITS) >= 
              game_state.type_cost(SCRAMBLER) and len(deploy_locations) > 0):
           
            """
            Choose a random deploy location.
            """
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(SCRAMBLER, deploy_location)
            """
            We don't have to remove the location since multiple information 
            units can occupy the same space.
            """
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def get_diagnostics(self, game_state):
        return

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
