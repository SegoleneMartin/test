import torch
from src.utils import Logger
import os
from itertools import cycle

class Tasks_Generator:
    def __init__(self, k_eff, shot, n_query, n_ways, loader_support, loader_query, train_mean, log_file):
        self.k_eff = k_eff
        self.shot = shot
        self.n_query = n_query
        self.loader_support = loader_support
        self.loader_query = loader_query
        self.log_file = log_file
        self.logger = Logger(__name__, log_file)
        self.train_mean = train_mean
        self.n_ways = n_ways

    def get_task(self, data_support, data_query, labels_support, labels_query):
        """
        inputs:
            data_support : torch.tensor of shape [shot * k_eff, channels, H, W]
            data_query : torch.tensor of shape [n_query, channels, H, W]
            labels_support :  torch.tensor of shape [shot * k_eff + n_query]
            labels_query :  torch.tensor of shape [n_query]
        returns :
            task : Dictionnary : x_support : torch.tensor of shape [k_eff * shot, channels, H, W]
                                 x_query : torch.tensor of shape [n_query, channels, H, W]
                                 y_support : torch.tensor of shape [k_eff * shot]
                                 y_query : torch.tensor of shape [n_query]
        """

        unique_labels = torch.unique(labels_support)
        new_labels_support = torch.zeros_like(labels_support)
        new_labels_query = torch.zeros_like(labels_query)
        for j, y in enumerate(unique_labels):
            new_labels_support[labels_support == y] = j
            new_labels_query[labels_query == y] = j
        labels_support = new_labels_support
        labels_query = new_labels_query

        task = {'x_s': data_support, 'y_s': labels_support.long(),
                'x_q': data_query, 'y_q': labels_query.long()}
        return task

    def generate_tasks(self):
        """

        returns :
            merged_task : { x_support : torch.tensor of shape [batch_size, k_eff * shot, channels, H, W]
                            x_query : torch.tensor of shape [batch_size, k_eff * query_shot, channels, H, W]
                            y_support : torch.tensor of shape [batch_size, k_eff * shot]
                            y_query : torch.tensor of shape [batch_size, k_eff * query_shot]
                            train_mean: torch.tensor of shape [feature_dim]}
        """
        tasks_dics = []

        for support, query in zip(self.loader_support, self.loader_query):
            (data_support, labels_support) = support
            (data_query, labels_query) = query
            task = self.get_task(data_support, data_query, labels_support, labels_query)
            tasks_dics.append(task)
            data_support = data_support.detach()

        feature_size = data_support.size()[-1]
        
        # Now merging all tasks into 1 single dictionnary
        merged_tasks = {}
        n_tasks = len(tasks_dics)
        for key in tasks_dics[0].keys():
            n_samples = tasks_dics[0][key].size(0)
            if key == 'x_s' or key == 'x_q':
                merged_tasks[key] = torch.cat([tasks_dics[i][key] for i in range(n_tasks)], dim=0).view(n_tasks,
                                                                                                        n_samples, feature_size)
            else:
                merged_tasks[key] = torch.cat([tasks_dics[i][key] for i in range(n_tasks)], dim=0).view(n_tasks,
                                                                                                        n_samples, -1)
        merged_tasks['train_mean'] = self.train_mean

        return merged_tasks
