import pytest
from django.utils import timezone

from apps.applications.services import ApplicationService
from apps.applications.models import (
    OpportunityQuestion,
    ApplicationAnswer,
    Interview,
    ApplicationEvent,
)


class TestApplicationServiceScreeningQuestions:
    """Test screening question methods in ApplicationService."""

    def test_upsert_screening_question_create(self, opportunity):
        """Test creating a new screening question."""
        service = ApplicationService()

        question = service.upsert_screening_question(
            opportunity_id=str(opportunity.id),
            payload={
                "question_text": "Why do you want this job?",
                "question_type": "text",
                "is_required": True,
                "order": 1,
                "config": {"max_length": 500}
            }
        )

        assert question.opportunity == opportunity
        assert question.question_text == "Why do you want this job?"
        assert question.question_type == "text"
        assert question.is_required is True
        assert question.order == 1
        assert question.config == {"max_length": 500}

    def test_upsert_screening_question_update(self, opportunity):
        """Test updating an existing screening question."""
        service = ApplicationService()

        # Create initial question
        question = OpportunityQuestion.objects.create(
            opportunity=opportunity,
            question_text="Initial question",
            question_type="text",
            order=1
        )

        # Update it
        updated_question = service.upsert_screening_question(
            opportunity_id=str(opportunity.id),
            payload={
                "id": str(question.id),
                "question_text": "Updated question",
                "question_type": "boolean",
                "is_required": False,
                "order": 2,
                "config": {"default": False}
            }
        )

        assert updated_question.id == question.id
        assert updated_question.question_text == "Updated question"
        assert updated_question.question_type == "boolean"
        assert updated_question.is_required is False
        assert updated_question.order == 2
        assert updated_question.config == {"default": False}

    def test_delete_screening_question(self, opportunity):
        """Test deleting a screening question."""
        service = ApplicationService()

        question = OpportunityQuestion.objects.create(
            opportunity=opportunity,
            question_text="Test question",
            question_type="text"
        )

        service.delete_screening_question(str(question.id))

        assert not OpportunityQuestion.objects.filter(id=question.id).exists()


class TestApplicationServiceAnswerSubmission:
    """Test answer submission methods in ApplicationService."""

    def test_submit_answers_text_question(self, application, opportunity):
        """Test submitting answers for text questions."""
        service = ApplicationService()

        # Create questions
        q1 = OpportunityQuestion.objects.create(
            opportunity=application.opportunity,
            question_text="Why this job?",
            question_type="text",
            order=1
        )
        q2 = OpportunityQuestion.objects.create(
            opportunity=application.opportunity,
            question_text="Tell us about yourself",
            question_type="text",
            order=2
        )

        answers_payload = [
            {
                "question_id": str(q1.id),
                "answer_text": "Because I'm passionate"
            },
            {
                "question_id": str(q2.id),
                "answer_text": "I'm a dedicated professional"
            }
        ]

        answers = service.submit_answers(str(application.id), answers_payload)

        assert len(answers) == 2

        # Check answers were created
        answer1 = ApplicationAnswer.objects.get(application=application, question=q1)
        answer2 = ApplicationAnswer.objects.get(application=application, question=q2)

        assert answer1.answer_text == "Because I'm passionate"
        assert answer2.answer_text == "I'm a dedicated professional"
        assert not answer1.is_disqualifying
        assert not answer2.is_disqualifying

    def test_submit_answers_boolean_question(self, application, opportunity):
        """Test submitting answers for boolean questions with disqualification."""
        service = ApplicationService()

        # Create boolean question with disqualification rule
        question = OpportunityQuestion.objects.create(
            opportunity=application.opportunity,
            question_text="Do you have a driver's license?",
            question_type="boolean",
            order=1,
            config={"disqualify_when": False}  # Disqualify when answer is False
        )

        # Submit disqualifying answer
        answers_payload = [{
            "question_id": str(question.id),
            "answer_text": "false"  # This should be converted to boolean
        }]

        answers = service.submit_answers(str(application.id), answers_payload)

        assert len(answers) == 1
        answer = answers[0]
        assert answer.is_disqualifying is True

    def test_submit_answers_choice_questions(self, application, opportunity):
        """Test submitting answers for choice questions with disqualification."""
        service = ApplicationService()

        # Create single choice question
        question = OpportunityQuestion.objects.create(
            opportunity=application.opportunity,
            question_text="What's your experience level?",
            question_type="single_choice",
            order=1,
            config={
                "options": ["Junior", "Mid", "Senior"],
                "disqualify_options": ["Junior"]
            }
        )

        # Submit disqualifying answer
        answers_payload = [{
            "question_id": str(question.id),
            "answer_options": ["Junior"]
        }]

        answers = service.submit_answers(str(application.id), answers_payload)

        assert len(answers) == 1
        answer = answers[0]
        assert answer.is_disqualifying is True
        assert answer.answer_options == ["Junior"]

    def test_submit_answers_number_question(self, application, opportunity):
        """Test submitting answers for number questions with range validation."""
        service = ApplicationService()

        # Create number question with min/max
        question = OpportunityQuestion.objects.create(
            opportunity=application.opportunity,
            question_text="Years of experience?",
            question_type="number",
            order=1,
            config={"min": 2, "max": 10}
        )

        # Test disqualifying answers
        answers_payload = [
            {"question_id": str(question.id), "answer_text": "1"},  # Too low
            {"question_id": str(question.id), "answer_text": "15"}  # Too high
        ]

        answers = service.submit_answers(str(application.id), answers_payload)

        # Should create two answers, both disqualifying
        assert len(answers) == 2
        for answer in answers:
            assert answer.is_disqualifying is True

    def test_submit_answers_invalid_question_id(self, application):
        """Test submitting answers for non-existent questions."""
        service = ApplicationService()

        # Try to answer a non-existent question
        answers_payload = [{
            "question_id": "00000000-0000-0000-0000-000000000000",
            "answer_text": "Test answer"
        }]

        # Should not raise error, just skip invalid questions
        answers = service.submit_answers(str(application.id), answers_payload)

        # No answers should be created for invalid questions
        assert len(answers) == 0

    def test_submit_answers_updates_existing(self, application, opportunity):
        """Test that submitting answers updates existing answers."""
        service = ApplicationService()

        question = OpportunityQuestion.objects.create(
            opportunity=application.opportunity,
            question_text="Test question",
            question_type="text"
        )

        # Submit initial answer
        answers_payload = [{
            "question_id": str(question.id),
            "answer_text": "Initial answer"
        }]
        service.submit_answers(str(application.id), answers_payload)

        # Update the answer
        answers_payload = [{
            "question_id": str(question.id),
            "answer_text": "Updated answer"
        }]
        answers = service.submit_answers(str(application.id), answers_payload)

        assert len(answers) == 1
        answer = answers[0]
        assert answer.answer_text == "Updated answer"


class TestApplicationServiceInterviewScheduling:
    """Test interview scheduling methods in ApplicationService."""

    def test_schedule_interview_minimal(self, application):
        """Test scheduling a basic interview."""
        service = ApplicationService()

        start_time = timezone.now()
        end_time = start_time.replace(hour=start_time.hour + 1)

        interview = service.schedule_interview_minimal(
            application_id=str(application.id),
            round_name="Technical Interview",
            scheduled_start=start_time,
            scheduled_end=end_time,
            location_type="virtual",
            location_details="Zoom Meeting"
        )

        assert interview.application == application
        assert interview.round_name == "Technical Interview"
        assert interview.scheduled_start == start_time
        assert interview.scheduled_end == end_time
        assert interview.location_type == "virtual"
        assert interview.location_details == "Zoom Meeting"
        assert interview.outcome == "pending"

        # Check that interview was saved
        assert Interview.objects.filter(id=interview.id).exists()

    def test_schedule_interview_creates_event(self, application):
        """Test that scheduling interview creates audit event."""
        service = ApplicationService()

        start_time = timezone.now()
        end_time = start_time.replace(hour=start_time.hour + 1)

        service.schedule_interview_minimal(
            application_id=str(application.id),
            round_name="Technical Interview",
            scheduled_start=start_time,
            scheduled_end=end_time
        )

        event = ApplicationEvent.objects.filter(
            application=application,
            event_type="note_added"
        ).first()

        assert event is not None
        assert "interview" in event.metadata
        assert event.metadata["interview"]["round_name"] == "Technical Interview"
