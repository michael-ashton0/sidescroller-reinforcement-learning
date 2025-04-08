
from collections import deque
from typing import Tuple
import numpy as np
import random
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


class DQN(nn.Module):
    ''' 
    Simple fully-connected feedforward MLP network.
    '''

    # We could have added training code as a method in this class,
    # but chose to go the simplest route.

    def __init__(self, 
                 obs_size:int, 
                 n_actions:int, 
                 lr_alpha:float=1e-4):
        '''
        Initializes a new instance of the DQN model for reinforcement learning.

        Parameters:
        - obs_size (int): The size of the input observation vector.
        - n_actions (int): The number of discrete actions.
        - lr_alpha (float): The learning rate for the optimizer.
        '''
        super().__init__()
        self.fc1 = nn.Linear(obs_size, 512)
        self.fc2 = nn.Linear(512, 256)
        self.fc3 = nn.Linear(256, 128)
        self.out = nn.Linear(128, n_actions)
        self.optimizer = optim.Adam(self.parameters(), lr=lr_alpha)


    def forward(self, 
                x:torch.Tensor):
        '''
        Performs a forward pass through the network.

        Parameters:
        - x (torch.Tensor): A tensor of shape (batch_size, obs_size)
        representing the input observations.

        Returns:
        - torch.Tensor: A tensor of shape (batch_size, n_actions) containing
        the predicted Q-values for each action.
        '''
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        return self.out(x)
    

    def backpropagate(self, 
                      qvalues:torch.Tensor, 
                      targets:torch.Tensor, 
                      use_huber:bool=True):
        '''
        Performs a backward pass and updates the network weights using gradient
        descent.

        Parameters:
        - qvalues (torch.Tensor): The predicted Q-values from the network.
        Typically shape (batch_size, n_actions).
        - targets (torch.Tensor): The target Q-values computed from the Bellman
        equation. Same shape as `qvalues`.
        - use_huber (bool): If True, uses the Huber loss (smooth L1 loss);
        otherwise, uses mean squared error (MSE) loss.

        Returns:
        - None
        '''
        # Move the variables to the correct CPU/GPU device
        device = next(self.parameters()).device
        qvalues = qvalues.to(device)
        targets = targets.to(device)
        
        # Perform backpropagation and update the weights
        loss_fn = F.smooth_l1_loss if use_huber else F.mse_loss
        loss = loss_fn(qvalues, targets)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()


class ReplayBuffer:
    '''
    Maintains a queue of previous action/observation values
    '''

    def __init__(self, 
                 capacity:int=100_000):
        '''
        Initializes the replay buffer with a maximum capacity.

        Parameters:
        - capacity (int): The maximum number of transitions to store.
        '''        
        self.buffer = deque(maxlen=capacity)

    def push(self, 
             transition:Tuple):
        '''
        Adds a transition tuple to the buffer.

        Parameters:
        - transition: A tuple of (state, action, reward, next_state, done).
        '''        
        self.buffer.append(transition)

    def sample(self, 
               batch_size:int):
        '''
        Samples a random batch of transitions from the buffer.

        Parameters:
        - batch_size (int): The number of transitions to sample.

        Returns:
        - tuple of torch.Tensor: Batch of states, actions, rewards, next_states, and dones.
        '''        
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        return (
            torch.tensor(np.array(states), dtype=torch.float32).squeeze(1),
            torch.tensor(actions, dtype=torch.int64),
            torch.tensor(rewards, dtype=torch.float32),
            torch.tensor(np.array(next_states), dtype=torch.float32),
            torch.tensor(dones, dtype=torch.float32),
        )

    def clear(self):
        '''
        Empties all stored transitions from the buffer.
        '''
        self.buffer.clear()

    def __len__(self):
        return len(self.buffer)


if __name__ == '__main__':  
    print(f"'{__file__}' defines a DQN network and is meant to be imported\n")
