"""
Tests for applications app API endpoints.
"""
import json
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from ninja.testing import TestClient
from apps.applications.api import applications_router
from apps.applications.models import Application, StageTemplate, ApplicationStageInstance
from apps.profiles.models import Profile
from apps.opportunities.models import Opportunity
from apps.organisations.models import Organisation
from apps.applications.services import ApplicationService


class ApplicationsAPITest(TestCase):
    """Test applications API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Skip Ninja API registry validation for tests
        import os
        os.environ['NINJA_SKIP_REGISTRY'] = '1'

        self.client = TestClient(applications_router)

        # Create test dependencies
        self.organisation = Organisation.objects.create(name="Test Company")
        self.profile = Profile.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        self.opportunity = Opportunity.objects.create(
            title="Software Engineer",
            organisation=self.organisation
        )

        # Seed default stages using the service
        service = ApplicationService()
        self.default_stages = service.seed_default_stages()

    def test_list_applications_empty(self):
        """Test listing applications when empty."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_application_success(self):
        """Test creating an application successfully."""
        data = {
            "profile_id": str(self.profile.id),
            "opportunity_id": str(self.opportunity.id),
            "organisation_id": str(self.organisation.id),
            "source": "direct"
        }

        response = self.client.post("/", json=data)
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertEqual(result["profile_id"], str(self.profile.id))
        self.assertEqual(result["opportunity_title"], self.opportunity.title)
        self.assertEqual(result["organisation_name"], self.organisation.name)
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["source"], "direct")

        # Check that application was created in database
        application = Application.objects.get(id=result["id"])
        self.assertEqual(application.status, "applied")
        self.assertEqual(application.source, "direct")

        # Check that stage instance was created
        self.assertIsNotNone(application.current_stage_instance)
        self.assertEqual(application.current_stage_instance.stage_template.slug, "applied")

    def test_create_application_duplicate(self):
        """Test creating duplicate application (should not create new one)."""
        # Create first application
        data = {
            "profile_id": str(self.profile.id),
            "opportunity_id": str(self.opportunity.id),
            "organisation_id": str(self.organisation.id),
            "source": "direct"
        }

        response1 = self.client.post("/", json=data)
        self.assertEqual(response1.status_code, 200)

        # Try to create the same application again
        response2 = self.client.post("/", json=data)
        self.assertEqual(response2.status_code, 200)

        # Should return the same application
        result1 = response1.json()
        result2 = response2.json()
        self.assertEqual(result1["id"], result2["id"])

        # Should still only have one application in database
        applications = Application.objects.filter(
            profile=self.profile,
            opportunity=self.opportunity
        )
        self.assertEqual(applications.count(), 1)

    def test_create_application_invalid_profile(self):
        """Test creating application with invalid profile ID."""
        import uuid
        fake_uuid = str(uuid.uuid4())

        data = {
            "profile_id": fake_uuid,
            "opportunity_id": str(self.opportunity.id),
            "organisation_id": str(self.organisation.id),
            "source": "direct"
        }

        response = self.client.post("/", json=data)
        # This should fail with a 404 error (Profile not found)
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["error"], "Profile not found")

    def test_create_application_invalid_opportunity(self):
        """Test creating application with invalid opportunity ID."""
        import uuid
        fake_uuid = str(uuid.uuid4())

        data = {
            "profile_id": str(self.profile.id),
            "opportunity_id": fake_uuid,
            "organisation_id": str(self.organisation.id),
            "source": "direct"
        }

        response = self.client.post("/", json=data)
        # This should fail with a 404 error (Opportunity not found)
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["error"], "Opportunity not found")

    def test_get_application_success(self):
        """Test getting a specific application."""
        # Create an application first
        data = {
            "profile_id": str(self.profile.id),
            "opportunity_id": str(self.opportunity.id),
            "organisation_id": str(self.organisation.id),
            "source": "direct"
        }
        create_response = self.client.post("/", json=data)
        application_id = create_response.json()["id"]

        # Now get the application
        response = self.client.get(f"/{application_id}")
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertEqual(result["id"], application_id)
        self.assertEqual(result["profile_id"], str(self.profile.id))
        self.assertEqual(result["opportunity_title"], self.opportunity.title)
        self.assertEqual(result["organisation_name"], self.organisation.name)
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["source"], "direct")

        # Check current stage information
        self.assertIsNotNone(result["current_stage"])
        self.assertEqual(result["current_stage"]["stage_name"], "Applied")
        self.assertTrue(result["current_stage"]["is_open"])

    def test_get_application_not_found(self):
        """Test getting an application that doesn't exist."""
        import uuid
        fake_uuid = str(uuid.uuid4())

        response = self.client.get(f"/{fake_uuid}")
        # This should fail with a 404 error (Application not found)
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["error"], "Application not found")

    def test_list_applications_with_data(self):
        """Test listing applications when data exists."""
        # Create multiple applications
        profiles_data = [
            ("Jane", "Smith", "jane@example.com"),
            ("Bob", "Johnson", "bob@example.com"),
        ]

        opportunities_data = [
            "Frontend Developer",
            "Backend Engineer",
        ]

        applications = []
        for i, (first, last, email) in enumerate(profiles_data):
            profile = Profile.objects.create(
                first_name=first,
                last_name=last,
                email=email
            )
            opportunity = Opportunity.objects.create(
                title=opportunities_data[i],
                organisation=self.organisation
            )

            data = {
                "profile_id": str(profile.id),
                "opportunity_id": str(opportunity.id),
                "organisation_id": str(self.organisation.id),
                "source": "direct"
            }
            response = self.client.post("/", json=data)
            applications.append(response.json())

        # Now list all applications
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        results = response.json()
        self.assertEqual(len(results), len(applications))

        # Check that all applications are in the results
        result_ids = {app["id"] for app in results}
        expected_ids = {app["id"] for app in applications}
        self.assertEqual(result_ids, expected_ids)

    def test_application_with_different_sources(self):
        """Test creating applications with different source types."""
        sources = ["direct", "referral", "internal", "import", "agency"]

        applications = []
        for source in sources:
            # Create a new profile for each application
            profile = Profile.objects.create(
                first_name=f"Test{source}",
                last_name="User",
                email=f"test{source}@example.com"
            )

            data = {
                "profile_id": str(profile.id),
                "opportunity_id": str(self.opportunity.id),
                "organisation_id": str(self.organisation.id),
                "source": source
            }

            response = self.client.post("/", json=data)
            self.assertEqual(response.status_code, 200)
            applications.append(response.json())

        # Verify all sources were saved correctly
        for i, source in enumerate(sources):
            application = Application.objects.get(id=applications[i]["id"])
            self.assertEqual(application.source, source)


# -----------------------------
# Stage Management API Tests
# -----------------------------

class StagesAPITest(TestCase):
    """Test stage management API endpoints."""

    def setUp(self):
        """Set up test data."""
        import os
        os.environ['NINJA_SKIP_REGISTRY'] = '1'

        self.client = TestClient(applications_router)

    def test_list_stages_empty(self):
        """Test listing stages when empty."""
        response = self.client.get("/stages/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_stages_with_data(self):
        """Test listing stages with data."""
        from apps.applications.services import ApplicationService
        service = ApplicationService()
        service.seed_default_stages()

        response = self.client.get("/stages/")
        self.assertEqual(response.status_code, 200)

        stages = response.json()
        self.assertGreater(len(stages), 0)

        # Check structure of first stage
        stage = stages[0]
        self.assertIn("id", stage)
        self.assertIn("name", stage)
        self.assertIn("slug", stage)
        self.assertIn("order", stage)
        self.assertIn("is_terminal", stage)

    def test_seed_default_stages(self):
        """Test seeding default stages."""
        response = self.client.post("/seed-stages/")
        self.assertEqual(response.status_code, 200)

        stages = response.json()
        self.assertEqual(len(stages), 7)  # Should have 7 default stages

        stage_names = [stage["name"] for stage in stages]
        expected_names = ["Applied", "In Review", "Interview", "Offer", "Hired", "Rejected", "Withdrawn"]
        self.assertEqual(set(stage_names), set(expected_names))


# -----------------------------
# Application Actions API Tests
# -----------------------------

class ApplicationActionsAPITest(TestCase):
    """Test application action API endpoints."""

    def setUp(self):
        """Set up test data."""
        import os
        os.environ['NINJA_SKIP_REGISTRY'] = '1'

        self.client = TestClient(applications_router)

        # Create test dependencies
        self.organisation = Organisation.objects.create(name="Test Company")
        self.profile = Profile.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        self.opportunity = Opportunity.objects.create(
            title="Software Engineer",
            organisation=self.organisation
        )

        # Seed default stages
        from apps.applications.services import ApplicationService
        service = ApplicationService()
        service.seed_default_stages()

        # Create an application
        response = self.client.post("/", json={
            "profile_id": str(self.profile.id),
            "opportunity_id": str(self.opportunity.id),
            "organisation_id": str(self.organisation.id),
            "source": "direct"
        })
        self.application_id = response.json()["id"]

    def test_change_stage_success(self):
        """Test changing application stage successfully."""
        response = self.client.post(f"/{self.application_id}/change-stage/", json={
            "stage_slug": "in_review"
        })
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertEqual(result["status"], "in_review")
        self.assertIsNotNone(result["current_stage"])
        self.assertEqual(result["current_stage"]["stage_name"], "In Review")

    def test_change_stage_invalid_application(self):
        """Test changing stage for non-existent application."""
        import uuid
        fake_uuid = str(uuid.uuid4())

        response = self.client.post(f"/{fake_uuid}/change-stage/", json={
            "stage_slug": "in_review"
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Application not found"})

    def test_change_stage_invalid_stage(self):
        """Test changing to invalid stage."""
        response = self.client.post(f"/{self.application_id}/change-stage/", json={
            "stage_slug": "invalid_stage"
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Invalid stage"})

    def test_withdraw_application_success(self):
        """Test withdrawing application successfully."""
        response = self.client.post(f"/{self.application_id}/withdraw/", json={
            "reason": "Changed my mind"
        })
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertEqual(result["status"], "withdrawn")

    def test_withdraw_application_invalid(self):
        """Test withdrawing non-existent application."""
        import uuid
        fake_uuid = str(uuid.uuid4())

        response = self.client.post(f"/{fake_uuid}/withdraw/", json={})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Application not found"})

    def test_record_decision_hired(self):
        """Test recording hire decision."""
        response = self.client.post(f"/{self.application_id}/decision/", json={
            "status": "hired",
            "reason": "Great fit for the team"
        })
        self.assertEqual(response.status_code, 200)

        result = response.json()
        self.assertEqual(result["status"], "hired")

    def test_record_decision_invalid_status(self):
        """Test recording invalid decision status."""
        response = self.client.post(f"/{self.application_id}/decision/", json={
            "status": "invalid_status"
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Invalid decision status"})


# -----------------------------
# Screening API Tests
# -----------------------------

class ScreeningAPITest(TestCase):
    """Test screening API endpoints."""

    def setUp(self):
        """Set up test data."""
        import os
        os.environ['NINJA_SKIP_REGISTRY'] = '1'

        self.client = TestClient(applications_router)

        # Create test dependencies
        self.organisation = Organisation.objects.create(name="Test Company")
        self.profile = Profile.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        self.opportunity = Opportunity.objects.create(
            title="Software Engineer",
            organisation=self.organisation
        )

        # Create an application
        response = self.client.post("/", json={
            "profile_id": str(self.profile.id),
            "opportunity_id": str(self.opportunity.id),
            "organisation_id": str(self.organisation.id),
            "source": "direct"
        })
        self.application_id = response.json()["id"]

    def test_get_application_questions_empty(self):
        """Test getting questions when none exist."""
        response = self.client.get(f"/{self.application_id}/questions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_application_questions_with_data(self):
        """Test getting questions when they exist."""
        from apps.applications.models import OpportunityQuestion

        # Create some questions
        q1 = OpportunityQuestion.objects.create(
            opportunity=self.opportunity,
            question_text="Why do you want this job?",
            question_type="text",
            order=1
        )
        q2 = OpportunityQuestion.objects.create(
            opportunity=self.opportunity,
            question_text="What's your experience?",
            question_type="number",
            order=2
        )

        response = self.client.get(f"/{self.application_id}/questions/")
        self.assertEqual(response.status_code, 200)

        questions = response.json()
        self.assertEqual(len(questions), 2)

        # Check question structure
        question_texts = [q["question_text"] for q in questions]
        self.assertIn("Why do you want this job?", question_texts)
        self.assertIn("What's your experience?", question_texts)

    def test_submit_screening_answers_success(self):
        """Test submitting screening answers successfully."""
        from apps.applications.models import OpportunityQuestion

        # Create a question
        question = OpportunityQuestion.objects.create(
            opportunity=self.opportunity,
            question_text="Why do you want this job?",
            question_type="text",
            order=1
        )

        response = self.client.post(f"/{self.application_id}/answers/", json={
            "answers": [{
                "question_id": str(question.id),
                "answer_text": "Because I'm passionate about it"
            }]
        })
        self.assertEqual(response.status_code, 200)

        answers = response.json()
        self.assertEqual(len(answers), 1)
        self.assertEqual(answers[0]["answer_text"], "Because I'm passionate about it")

    def test_get_application_answers(self):
        """Test getting application answers."""
        from apps.applications.models import OpportunityQuestion, ApplicationAnswer

        # Create question and answer
        question = OpportunityQuestion.objects.create(
            opportunity=self.opportunity,
            question_text="Test question",
            question_type="text"
        )

        answer = ApplicationAnswer.objects.create(
            application_id=self.application_id,
            question=question,
            answer_text="Test answer"
        )

        response = self.client.get(f"/{self.application_id}/answers/")
        self.assertEqual(response.status_code, 200)

        answers = response.json()
        self.assertEqual(len(answers), 1)
        self.assertEqual(answers[0]["answer_text"], "Test answer")


# -----------------------------
# Interview API Tests
# -----------------------------

class InterviewAPITest(TestCase):
    """Test interview API endpoints."""

    def setUp(self):
        """Set up test data."""
        import os
        os.environ['NINJA_SKIP_REGISTRY'] = '1'

        self.client = TestClient(applications_router)

        # Create test dependencies
        self.organisation = Organisation.objects.create(name="Test Company")
        self.profile = Profile.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        self.opportunity = Opportunity.objects.create(
            title="Software Engineer",
            organisation=self.organisation
        )

        # Create an application
        response = self.client.post("/", json={
            "profile_id": str(self.profile.id),
            "opportunity_id": str(self.opportunity.id),
            "organisation_id": str(self.organisation.id),
            "source": "direct"
        })
        self.application_id = response.json()["id"]

    def test_schedule_interview_success(self):
        """Test scheduling interview successfully."""
        from datetime import datetime, timedelta

        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)

        response = self.client.post(f"/{self.application_id}/interviews/", json={
            "round_name": "Technical Interview",
            "scheduled_start": start_time.isoformat(),
            "scheduled_end": end_time.isoformat(),
            "location_type": "virtual",
            "location_details": "Zoom Meeting"
        })
        self.assertEqual(response.status_code, 201)

        interview = response.json()
        self.assertEqual(interview["round_name"], "Technical Interview")
        self.assertEqual(interview["location_type"], "virtual")

    def test_schedule_interview_invalid_application(self):
        """Test scheduling interview for non-existent application."""
        import uuid
        fake_uuid = str(uuid.uuid4())

        from datetime import datetime, timedelta
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)

        response = self.client.post(f"/{fake_uuid}/interviews/", json={
            "round_name": "Technical Interview",
            "scheduled_start": start_time.isoformat(),
            "scheduled_end": end_time.isoformat()
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Application not found"})

    def test_get_application_interviews_empty(self):
        """Test getting interviews when none exist."""
        response = self.client.get(f"/{self.application_id}/interviews/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_application_interviews_with_data(self):
        """Test getting interviews when they exist."""
        from datetime import datetime, timedelta
        from apps.applications.models import Interview

        # Create an interview
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)

        interview = Interview.objects.create(
            application_id=self.application_id,
            round_name="Technical Interview",
            scheduled_start=start_time,
            scheduled_end=end_time,
            location_type="virtual"
        )

        response = self.client.get(f"/{self.application_id}/interviews/")
        self.assertEqual(response.status_code, 200)

        interviews = response.json()
        self.assertEqual(len(interviews), 1)
        self.assertEqual(interviews[0]["round_name"], "Technical Interview")


# -----------------------------
# Event History API Tests
# -----------------------------

class EventHistoryAPITest(TestCase):
    """Test event history API endpoints."""

    def setUp(self):
        """Set up test data."""
        import os
        os.environ['NINJA_SKIP_REGISTRY'] = '1'

        self.client = TestClient(applications_router)

        # Create test dependencies
        self.organisation = Organisation.objects.create(name="Test Company")
        self.profile = Profile.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        self.opportunity = Opportunity.objects.create(
            title="Software Engineer",
            organisation=self.organisation
        )

        # Create an application
        response = self.client.post("/", json={
            "profile_id": str(self.profile.id),
            "opportunity_id": str(self.opportunity.id),
            "organisation_id": str(self.organisation.id),
            "source": "direct"
        })
        self.application_id = response.json()["id"]

    def test_get_application_events_empty(self):
        """Test getting events when none exist."""
        response = self.client.get(f"/{self.application_id}/events/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_application_events_with_data(self):
        """Test getting events when they exist."""
        from apps.applications.models import ApplicationEvent

        # Create an event
        event = ApplicationEvent.objects.create(
            application_id=self.application_id,
            event_type="stage_changed",
            metadata={"from_stage": "applied", "to_stage": "in_review"}
        )

        response = self.client.get(f"/{self.application_id}/events/")
        self.assertEqual(response.status_code, 200)

        events = response.json()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "stage_changed")
        self.assertEqual(events[0]["metadata"]["to_stage"], "in_review")

    def test_get_events_invalid_application(self):
        """Test getting events for non-existent application."""
        import uuid
        fake_uuid = str(uuid.uuid4())

        response = self.client.get(f"/{fake_uuid}/events/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
