from unittest.mock import patch

import pytest
from django.test import override_settings

from flaky import flaky
from rest_framework import status

from api.projects import queries
from api.projects.serializers import BookmarkedProjectSerializer, ProjectDetailSerializer
from constants.experiments import ExperimentLifeCycle
from constants.jobs import JobLifeCycle
from constants.urls import API_V1
from db.models.bookmarks import Bookmark
from db.models.build_jobs import BuildJob
from db.models.experiment_groups import ExperimentGroup
from db.models.experiments import Experiment
from db.models.jobs import Job
from db.models.notebooks import NotebookJob
from db.models.projects import Project
from db.models.tensorboards import TensorboardJob
from factories.factory_build_jobs import BuildJobFactory
from factories.factory_experiment_groups import ExperimentGroupFactory
from factories.factory_experiments import ExperimentFactory, ExperimentJobFactory
from factories.factory_jobs import JobFactory
from factories.factory_plugins import NotebookJobFactory, TensorboardJobFactory
from factories.factory_projects import ProjectFactory
from tests.utils import BaseViewTest


@pytest.mark.projects_mark
class TestProjectCreateViewV1(BaseViewTest):
    serializer_class = BookmarkedProjectSerializer
    model_class = Project
    factory_class = ProjectFactory
    num_objects = 3
    HAS_AUTH = True

    def setUp(self):
        super().setUp()
        self.url = '/{}/projects/'.format(API_V1)
        self.objects = [self.factory_class() for _ in range(self.num_objects)]
        self.queryset = self.model_class.objects.all()

    def test_create(self):
        data = {}
        resp = self.auth_client.post(self.url, data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        data = {'name': 'new_project'}
        resp = self.auth_client.post(self.url, data)
        assert resp.status_code == status.HTTP_201_CREATED
        assert self.model_class.objects.count() == self.num_objects + 1
        assert self.model_class.objects.last().owner.owner == self.auth_client.user

    @override_settings(ALLOW_USER_PROJECTS=False)
    def test_not_allowed_to_create(self):
        data = {'name': 'new_project'}
        resp = self.auth_client.post(self.url, data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.projects_mark
class TestProjectListViewV1(BaseViewTest):
    serializer_class = BookmarkedProjectSerializer
    model_class = Project
    factory_class = ProjectFactory
    num_objects = 3
    HAS_AUTH = True

    def setUp(self):
        super().setUp()
        self.user = self.auth_client.user
        self.url = '/{}/{}'.format(API_V1, self.user.username)
        self.objects = [self.factory_class(user=self.user) for _ in range(self.num_objects)]
        # Other user objects
        self.other_object = self.factory_class()
        # One private project
        self.private = self.factory_class(user=self.other_object.user, is_public=False)
        self.url_other = '/{}/{}'.format(API_V1, self.other_object.user)

        self.queryset = self.model_class.objects.filter(user=self.user)
        self.queryset = self.queryset.order_by('-updated_at')

    def test_get(self):
        resp = self.auth_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK

        assert resp.data['next'] is None
        assert resp.data['count'] == len(self.objects)

        data = resp.data['results']
        assert len(data) == self.queryset.count()
        assert data == self.serializer_class(self.queryset, many=True).data

    def test_get_with_bookmarked_objects(self):
        # Other user bookmark
        Bookmark.objects.create(
            user=self.other_object.user,
            content_object=self.objects[0])

        resp = self.auth_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        self.assertEqual(len([1 for obj in resp.data['results'] if obj['bookmarked'] is True]), 0)

        # Authenticated user bookmark
        Bookmark.objects.create(
            user=self.auth_client.user,
            content_object=self.objects[0])

        resp = self.auth_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert len([1 for obj in resp.data['results'] if obj['bookmarked'] is True]) == 1

    @flaky(max_runs=3)
    def test_get_others(self):
        resp = self.auth_client.get(self.url_other)
        assert resp.status_code == status.HTTP_200_OK

        assert resp.data['next'] is None
        assert resp.data['count'] == 1

        data = resp.data['results']
        assert len(data) == 1
        assert data[0] == self.serializer_class(self.other_object).data

    @flaky(max_runs=3)
    def test_pagination(self):
        limit = self.num_objects - 1
        resp = self.auth_client.get("{}?limit={}".format(self.url, limit))
        assert resp.status_code == status.HTTP_200_OK

        next_page = resp.data.get('next')
        assert next_page is not None
        assert resp.data['count'] == self.queryset.count()

        data = resp.data['results']
        assert len(data) == limit
        assert data == self.serializer_class(self.queryset[:limit], many=True).data

        resp = self.auth_client.get(next_page)
        assert resp.status_code == status.HTTP_200_OK

        assert resp.data['next'] is None

        data = resp.data['results']
        assert len(data) == 1
        assert data == self.serializer_class(self.queryset[limit:], many=True).data


@pytest.mark.projects_mark
class TestProjectDetailViewV1(BaseViewTest):
    serializer_class = ProjectDetailSerializer
    model_class = Project
    factory_class = ProjectFactory
    HAS_AUTH = True
    DISABLE_RUNNER = True

    def setUp(self):
        super().setUp()
        self.object = self.factory_class(user=self.auth_client.user)
        self.url = '/{}/{}/{}/'.format(API_V1, self.object.user.username, self.object.name)
        self.queryset = self.model_class.objects.filter(user=self.object.user)

        # Create related fields
        for _ in range(2):
            ExperimentGroupFactory(project=self.object)

        # Create related fields
        for _ in range(2):
            ExperimentFactory(project=self.object)

        # Other user objects
        self.other_object = self.factory_class()
        self.url_other = '/{}/{}/{}/'.format(API_V1,
                                             self.other_object.user.username,
                                             self.other_object.name)
        # One private project
        self.private = self.factory_class(is_public=False)
        self.url_private = '/{}/{}/{}/'.format(API_V1,
                                               self.private.user.username,
                                               self.private.name)

        self.object_query = queries.projects_details.get(id=self.object.id)
        self.other_object_query = queries.projects_details.get(id=self.other_object.id)

    def test_get(self):
        resp = self.auth_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == self.serializer_class(self.object_query).data
        assert resp.data['num_experiments'] == 2
        assert resp.data['num_experiment_groups'] == 2

        # Get other public project works
        resp = self.auth_client.get(self.url_other)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == self.serializer_class(self.other_object_query).data

        # Get other private project does not work
        resp = self.auth_client.get(self.url_private)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_patch(self):
        new_name = 'updated_project_name'
        data = {'name': new_name}
        assert self.object.name != data['name']
        resp = self.auth_client.patch(self.url, data=data)
        assert resp.status_code == status.HTTP_200_OK
        new_object = self.model_class.objects.get(id=self.object.id)
        assert new_object.user == self.object.user
        assert new_object.name != self.object.name
        assert new_object.name == new_name
        assert new_object.experiments.count() == 2
        assert new_object.experiment_groups.count() == 2

        # Patch does not work for other project public and private
        resp = self.auth_client.delete(self.url_other)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        resp = self.auth_client.delete(self.url_private)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_delete(self):
        assert self.queryset.count() == 1
        assert ExperimentGroup.objects.count() == 2
        assert Experiment.objects.count() == 2

        with patch('libs.paths.projects.delete_path') as delete_path_project_mock_stop:
            with patch('libs.paths.experiment_groups.delete_path') as delete_path_group_mock_stop:
                with patch('libs.paths.experiments.delete_path') as delete_path_xp_mock_stop:
                    resp = self.auth_client.delete(self.url)
        # 2 * project + 1 repo
        assert delete_path_project_mock_stop.call_count == 3
        # 2 * 2 * groups
        assert delete_path_group_mock_stop.call_count
        assert delete_path_xp_mock_stop.call_count == 4  # 2 * 2  * groups
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert self.queryset.count() == 0
        assert ExperimentGroup.objects.count() == 0
        assert Experiment.objects.count() == 0

        # Delete does not work for other project public and private
        resp = self.auth_client.delete(self.url_other)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        resp = self.auth_client.delete(self.url_private)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_delete_triggers_stopping_of_experiment_groups(self):
        assert self.queryset.count() == 1
        assert ExperimentGroup.objects.count() == 2
        experiment_group = ExperimentGroup.objects.first()
        # Add running experiment
        experiment = ExperimentFactory(project=experiment_group.project,
                                       experiment_group=experiment_group)
        # Set one experiment to running with one job
        experiment.set_status(ExperimentLifeCycle.SCHEDULED)
        # Add job
        ExperimentJobFactory(experiment=experiment)

        assert Experiment.objects.count() == 3
        with patch('scheduler.tasks.experiments.experiments_stop.apply_async') as xp_mock_stop:
            resp = self.auth_client.delete(self.url)
        assert xp_mock_stop.call_count == 1
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert self.queryset.count() == 0
        assert ExperimentGroup.objects.count() == 0
        assert Experiment.objects.count() == 0

        # Delete does not work for other project public and private
        resp = self.auth_client.delete(self.url_other)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        resp = self.auth_client.delete(self.url_private)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_delete_triggers_stopping_of_experiments(self):
        assert self.queryset.count() == 1
        assert ExperimentGroup.objects.count() == 2
        # Add experiment
        experiment = ExperimentFactory(project=self.object)
        # Set one experiment to running with one job
        experiment.set_status(ExperimentLifeCycle.SCHEDULED)
        # Add job
        ExperimentJobFactory(experiment=experiment)

        assert Experiment.objects.count() == 3
        with patch('scheduler.tasks.experiments.experiments_stop.apply_async') as xp_mock_stop:
            resp = self.auth_client.delete(self.url)
        assert xp_mock_stop.call_count == 1
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert self.queryset.count() == 0
        assert ExperimentGroup.objects.count() == 0
        assert Experiment.objects.count() == 0

        # Delete does not work for other project public and private
        resp = self.auth_client.delete(self.url_other)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        resp = self.auth_client.delete(self.url_private)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_delete_triggers_stopping_of_jobs(self):
        assert self.queryset.count() == 1
        for _ in range(2):
            job = JobFactory(project=self.object)
            job.set_status(JobLifeCycle.SCHEDULED)
        assert Job.objects.count() == 2

        with patch('scheduler.tasks.jobs.jobs_stop.apply_async') as job_mock_stop:
            resp = self.auth_client.delete(self.url)
        assert job_mock_stop.call_count == 2
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert self.queryset.count() == 0
        assert ExperimentGroup.objects.count() == 0
        assert Experiment.objects.count() == 0

        # Delete does not work for other project public and private
        resp = self.auth_client.delete(self.url_other)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        resp = self.auth_client.delete(self.url_private)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_delete_triggers_stopping_of_build_jobs(self):
        assert self.queryset.count() == 1
        for _ in range(2):
            job = BuildJobFactory(project=self.object)
            job.set_status(JobLifeCycle.SCHEDULED)
        assert BuildJob.objects.count() == 2

        with patch('scheduler.tasks.build_jobs.build_jobs_stop.apply_async') as job_mock_stop:
            resp = self.auth_client.delete(self.url)
        assert job_mock_stop.call_count == 2
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert self.queryset.count() == 0
        assert ExperimentGroup.objects.count() == 0
        assert Experiment.objects.count() == 0

        # Delete does not work for other project public and private
        resp = self.auth_client.delete(self.url_other)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        resp = self.auth_client.delete(self.url_private)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_delete_triggers_stopping_of_plugin_jobs(self):
        assert self.queryset.count() == 1

        notebook_job = NotebookJobFactory(project=self.object)
        notebook_job.set_status(JobLifeCycle.SCHEDULED)

        tensorboard_job = TensorboardJobFactory(project=self.object)
        tensorboard_job.set_status(JobLifeCycle.SCHEDULED)

        assert NotebookJob.objects.count() == 1
        assert TensorboardJob.objects.count() == 1

        with patch('scheduler.tasks.notebooks.'
                   'projects_notebook_stop.apply_async') as notebook_mock_stop:
            with patch('scheduler.tasks.tensorboards.'
                       'tensorboards_stop.apply_async') as tensorboard_mock_stop:
                resp = self.auth_client.delete(self.url)

        assert notebook_mock_stop.call_count == 1
        assert tensorboard_mock_stop.call_count == 1
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert self.queryset.count() == 0
        assert ExperimentGroup.objects.count() == 0
        assert Experiment.objects.count() == 0

        # Delete does not work for other project public and private
        resp = self.auth_client.delete(self.url_other)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        resp = self.auth_client.delete(self.url_private)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
