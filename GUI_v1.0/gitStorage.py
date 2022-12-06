# -*- coding: utf-8 -*-
"""
Created on Fri May 21 15:02:49 2021

@author: cca78
"""

import sys
from multiprocessing import Process, Queue
import gitlab
import base64
import os
from datetime import datetime
# from .models import Meme
import json


class Sync:
    def __init__(self):
        self.GitlabURL = "https://eng-git.canterbury.ac.nz/"
        self.access_token = "sY_ieZczMq1hyhiuPbbd"  
        self.project_id = "10347"
        self.progress = 0
        self.progressQueue = Queue()
    #
    # def create_file(self):
    #     f = project.files.create({'file_path': 'testfile.txt',
    #                               'branch': 'master',
    #                               'content': file_content,
    #                               'author_email': 'test@example.com',
    #                               'author_name': 'yourname',
    #                               'encoding': 'text',
    #                               'commit_message': 'Create testfile'})
    #
    # def sync(self):
    #     gl = gitlab.Gitlab(self.GitlabURL, self.access_token)
    #     # for meme in Meme.objects.all():
    #     #     meme_title = meme.meme_title
    #     #     meme_file = str(meme.meme_file)
    #
    #     root = settings.MEDIA_ROOT
    #     # place = os.path.join(root, meme_file)
    #
    #     # Create a new project on GitLab.
    #     project = gl.projects.create({'name': meme_title })
    #
    #     data = {
    #         'branch': 'master',
    #         'commit_message': 'Automatic commit via sync.py.',
    #         'actions': [
    #             {
    #                 # Binary files need to be base64 encoded
    #                 'action': 'create',
    #                 'file_path': place,
    #                 'content': base64.b64encode(open(place, "rb").read()),
    #                 'encoding': 'base64',
    #             }
    #         ]
    #         }
    #
    #     commit = project.commits.create(data)
    def commit_process(self, files, filepaths):
        self.commit_p = Process(target=self.commit_file, args=[files, filepaths])
        self.commit_p.start()

    def commit_file(self, files, filepaths):  # -> bool:
        """Commit a file to the repository

        Parameters
        ----------
        project_id: int
            the project id to commit into. E.g. 1582
        file_path: str
            the file path to commit. NOTE: expecting a path relative to the
            repo path. This will also be used as the path to commit into.
            If you want to use absolute local path you will also have to
            pass a parameter for the file relative repo path
        gitlab_url: str
            The gitlab url. E.g. https://gitlab.example.com
        private_token: str
            Private access token. See doc for more details
        branch: str
            The branch you are working in. See note below for more about this
        """
        gl = gitlab.Gitlab(self.GitlabURL, private_token=self.access_token)
        # print(gl)

        try:
            #     # get the project by the project id
            # print(gl.projects.list())
            project = gl.projects.get(self.project_id)
            #
            # commits = gl.project.list()
            # gl = gitlab.Gitlab('https://gitlab.com/*********', private_token='******************')
            gl.auth()
            # projects = gl.projects.list()
            # print(project.repository_tree())
            # return HttpResponse(projects[0].name)
            repo_tree = project.repository_tree()
            # print("Checking git")
            # print(project.repository_tree())
            # print("got tree")
            repo = []
            for r in repo_tree:
                repo.append(r['name'])
            # print(len(project.repository_tree()))
            # print(len(repo))
            # print(filepaths)
            # print(repo)
            for i in range(len(files)):
                # print(i)
                file_name = files[i]
                file_path = filepaths[i]
                self.progress = (100 * (i + 1)) / len(files)
                self.progressQueue.put(self.progress)
                # print(repo['name'])

                if (file_path.split("/")[-2] + "/" + file_name) not in repo:
                    # print('---------------------')
                    # print("uploading: " + file_path.split("\\")[-2])
                    # print('---------------------')
                    # print(file_name)
                    try:
                        data = {
                                'branch': 'master',
                                'commit_message': " " + file_path.split("/")[-2],
                                'actions': [
                                    {
                                        'action': 'create',
                                        'file_path': file_path.split("/")[-2] + "/" + file_name,
                                        'content': open(file_path).read(),
                                    }
                                        # {
                                        #     # Binary files need to be base64 encoded
                                        #     'action': 'create',
                                        #     'file_path': 'logo.png',
                                        #     'content': base64.b64encode(open('logo.png').read()),
                                        #     'encoding': 'base64',
                                        # }
                                ]
                            }
                        commit = project.commits.create(data)
                        # print('successfully commited')
                    except Exception as e:
                        print('couldnt upload ' + file_name)
                        print(e)
                else:
                    try:
                        data = {
                                'branch': 'master',
                                'commit_message': " " + file_path.split("/")[-2],
                                'actions': [
                                    {
                                        'action': 'update',
                                        'file_path': file_path.split("/")[-2] + "/" + file_name,
                                        'content': open(file_path).read(),
                                    }
                                    # {
                                    #     # Binary files need to be base64 encoded
                                    #     'action': 'create',
                                    #     'file_path': 'logo.png',
                                    #     'content': base64.b64encode(open('logo.png').read()),
                                    #     'encoding': 'base64',
                                    # }
                                ]
                            }
                        commit = project.commits.create(data)
                        # print('successfully commited')
                    except Exception as e:
                        print('couldnt upload ' + file_name)
                        print(e)
                        
            self.progress = 0
            self.progressQueue.put(1000)
            
            #
            #     # read the file contents
            # with open(file_path, 'r') as fin:
            #     content = fin.read()
            # timestamp_string = now.strftime("%d_%m_%Y_%H_%M_%S_")

            # file_data = {'branch': "master",
            #              'commit_message': 'Test completed' + datetime.now().strftime("%d_%m_%Y_%H_%M_%S_")}
            #

            # resp = project.files.create(file_data)
            # #     # do something with resp
        except gitlab.exceptions.GitlabGetError as get_error:
            # project does not exists
            print(f"could not find no project with id {self.project_id}: {get_error}")
            return False
        except gitlab.exceptions.GitlabCreateError as create_error:
            # project does not exists
            print(f"could not create file: {create_error}")
            return False
        # except gitlab.exceptions.GitlabConnectionError:
        #     print("no internet")

        return True


def check_ping():
    hostname = "google.com"
    system = sys.platform
    # print(system)
    if system == 'darwin':
        response = os.system("ping -c 1 " + hostname)
    else:
        response = os.system("ping -n 1 " + hostname)

    # and then check the response...
    if response == 0:
        pingstatus = 1  # "Network Active"
    else:
        pingstatus = 0  # "Network Error"

    return pingstatus