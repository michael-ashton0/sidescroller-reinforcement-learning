
from dataclasses import dataclass

@dataclass
class GameController():
    '''
    Logical representation of a game controller with a flag for each button
    '''
    
    mleft: bool = False
    mright: bool = False
    jump: bool = False
    shoot: bool = False
    throw: bool = False

    def reset(self):
        '''
        Resets all control flags to False.
        '''
        for field in self.__dataclass_fields__:
            setattr(self, field, False)

    def __repr__(self):
        '''
        Returns a compact string showing only active controls.
        '''
        buttons = [k for k,v in self.__dict__.items() if v]
        buttons = ', '.join(buttons) if buttons else 'None'
        return f"GameController[{buttons}]"