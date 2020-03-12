from simpleland.common import SLObject, SLBody, SLVector, SimClock
from simpleland.object_manager import SLObjectManager
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.game import SLGame
from simpleland.game_client import ClientConnector, GameClient
import time

def test():

    steps_per_second = 20

    # Add objects to game
    game = SLGame()    

    #*********
    #Setup
    obj = SLObject(SLBody(mass=50, moment=1))
    obj.set_position(position=SLVector(6, 6))
    obj.set_data_value("type","hostile")
    obj.set_data_value("energy", 100)
    SLShapeFactory.attach_circle(obj, 1)
    game.add_object(obj)

    game.process_events()
    game.apply_physics()
    game.tick()
    #*************
    game.process_events()
    game.apply_physics()
    game.tick()
    


def test2():
    connector = ClientConnector()
    #client = GameClient(connector)



test2()