# pylint:disable=ungrouped-imports

from unittest.mock import patch

import pytest

import activitylogs
import auditor
import tracker

from event_manager.events import tensorboard as tensorboard_events
from factories.factory_plugins import TensorboardJobFactory
from factories.factory_projects import ProjectFactory
from tests.utils import BaseTest


@pytest.mark.auditor_mark
class AuditorTensorboardTest(BaseTest):
    """Testing subscribed events"""
    DISABLE_RUNNER = True

    def setUp(self):
        self.tensorboard = TensorboardJobFactory(project=ProjectFactory())
        auditor.validate()
        auditor.setup()
        tracker.validate()
        tracker.setup()
        activitylogs.validate()
        activitylogs.setup()
        super().setUp()

    @patch('tracker.service.TrackerService.record_event')
    @patch('activitylogs.service.ActivityLogService.record_event')
    def test_tensorboard_started(self, activitylogs_record, tracker_record):
        auditor.record(event_type=tensorboard_events.TENSORBOARD_STARTED,
                       instance=self.tensorboard,
                       target='project')

        assert tracker_record.call_count == 1
        assert activitylogs_record.call_count == 0

    @patch('tracker.service.TrackerService.record_event')
    @patch('activitylogs.service.ActivityLogService.record_event')
    def test_tensorboard_started_triggered(self, activitylogs_record, tracker_record):
        auditor.record(event_type=tensorboard_events.TENSORBOARD_STARTED_TRIGGERED,
                       instance=self.tensorboard,
                       actor_id=1,
                       actor_name='foo',
                       target='project')

        assert tracker_record.call_count == 1
        assert activitylogs_record.call_count == 1

    @patch('tracker.service.TrackerService.record_event')
    @patch('activitylogs.service.ActivityLogService.record_event')
    def test_tensorboard_stopped(self, activitylogs_record, tracker_record):
        auditor.record(event_type=tensorboard_events.TENSORBOARD_STOPPED,
                       instance=self.tensorboard,
                       target='project')

        assert tracker_record.call_count == 1
        assert activitylogs_record.call_count == 0

    @patch('tracker.service.TrackerService.record_event')
    @patch('activitylogs.service.ActivityLogService.record_event')
    def test_tensorboard_stopped_triggered(self, activitylogs_record, tracker_record):
        auditor.record(event_type=tensorboard_events.TENSORBOARD_STOPPED_TRIGGERED,
                       instance=self.tensorboard,
                       actor_id=1,
                       actor_name='foo',
                       target='project')

        assert tracker_record.call_count == 1
        assert activitylogs_record.call_count == 1

    @patch('tracker.service.TrackerService.record_event')
    @patch('activitylogs.service.ActivityLogService.record_event')
    def test_tensorboard_viewed(self, activitylogs_record, tracker_record):
        auditor.record(event_type=tensorboard_events.TENSORBOARD_VIEWED,
                       instance=self.tensorboard,
                       actor_id=1,
                       actor_name='foo',
                       target='project')

        assert tracker_record.call_count == 1
        assert activitylogs_record.call_count == 1

    @patch('tracker.service.TrackerService.record_event')
    @patch('activitylogs.service.ActivityLogService.record_event')
    def test_tensorboard_unbookmarked(self, activitylogs_record, tracker_record):
        auditor.record(event_type=tensorboard_events.TENSORBOARD_UNBOOKMARKED,
                       instance=self.tensorboard,
                       actor_id=1,
                       actor_name='foo',
                       target='project')

        assert tracker_record.call_count == 1
        assert activitylogs_record.call_count == 1

    @patch('tracker.service.TrackerService.record_event')
    @patch('activitylogs.service.ActivityLogService.record_event')
    def test_tensorboard_bookmarked(self, activitylogs_record, tracker_record):
        auditor.record(event_type=tensorboard_events.TENSORBOARD_BOOKMARKED,
                       instance=self.tensorboard,
                       actor_id=1,
                       actor_name='foo',
                       target='project')

        assert tracker_record.call_count == 1
        assert activitylogs_record.call_count == 1

    @patch('tracker.service.TrackerService.record_event')
    @patch('activitylogs.service.ActivityLogService.record_event')
    def test_experiment_new_status(self, activitylogs_record, tracker_record):
        auditor.record(event_type=tensorboard_events.TENSORBOARD_NEW_STATUS,
                       instance=self.tensorboard,
                       target='project')

        assert tracker_record.call_count == 1
        assert activitylogs_record.call_count == 0

    @patch('tracker.service.TrackerService.record_event')
    @patch('activitylogs.service.ActivityLogService.record_event')
    def test_experiment_failed(self, activitylogs_record, tracker_record):
        auditor.record(event_type=tensorboard_events.TENSORBOARD_FAILED,
                       instance=self.tensorboard,
                       target='project')

        assert tracker_record.call_count == 1
        assert activitylogs_record.call_count == 0

    @patch('tracker.service.TrackerService.record_event')
    @patch('activitylogs.service.ActivityLogService.record_event')
    def test_experiment_succeeded(self, activitylogs_record, tracker_record):
        auditor.record(event_type=tensorboard_events.TENSORBOARD_SUCCEEDED,
                       instance=self.tensorboard,
                       target='project')

        assert tracker_record.call_count == 1
        assert activitylogs_record.call_count == 0
