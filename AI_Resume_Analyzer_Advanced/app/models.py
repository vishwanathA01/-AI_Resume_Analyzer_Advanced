from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user")
    created_at = db.Column(db.DateTime, default=_utcnow_naive)

    resumes = db.relationship("Resume", backref="user", lazy=True)
    profile_picture = db.relationship(
        "ProfilePicture", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    community_posts = db.relationship(
        "CommunityPost", back_populates="author", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ProfilePicture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    filename = db.Column(db.String(80), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=_utcnow_naive, nullable=False)

    user = db.relationship("User", back_populates="profile_picture")


class CommunityPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body = db.Column(db.String(1200), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow_naive, nullable=False, index=True)

    author = db.relationship("User", back_populates="community_posts")
    comments = db.relationship(
        "CommunityComment", back_populates="post", cascade="all, delete-orphan"
    )
    likes = db.relationship(
        "CommunityLike", back_populates="post", cascade="all, delete-orphan"
    )


class CommunityComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer, db.ForeignKey("community_post.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body = db.Column(db.String(600), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow_naive, nullable=False, index=True)

    post = db.relationship("CommunityPost", back_populates="comments")
    author = db.relationship("User")


class CommunityLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer, db.ForeignKey("community_post.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, default=_utcnow_naive, nullable=False)

    post = db.relationship("CommunityPost", back_populates="likes")
    user = db.relationship("User")
    __table_args__ = (
        db.UniqueConstraint("post_id", "user_id", name="uq_community_like_post_user"),
    )


class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    extracted_text = db.Column(db.Text, default="")
    resume_score = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=_utcnow_naive)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    company = db.Column(db.String(180), nullable=False)
    location = db.Column(db.String(180), default="Remote")
    description = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.Text, default="")
    min_experience = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=_utcnow_naive)
    is_active = db.Column(db.Boolean, default=True)
    categories = db.relationship(
        "JobCategory", secondary="job_category_job", back_populates="jobs"
    )

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey("resume.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    similarity_score = db.Column(db.Float, default=0)
    skill_score = db.Column(db.Float, default=0)
    final_score = db.Column(db.Float, default=0)
    missing_skills = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=_utcnow_naive)


class SavedJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=_utcnow_naive, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "job_id", name="uq_saved_job_user_job"),)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default="Interested")
    notes = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, default=_utcnow_naive, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, nullable=False)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(32), nullable=False, default="general")
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=_utcnow_naive, nullable=False)


class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    preferred_location = db.Column(db.String(180), nullable=False, default="")
    email_notifications = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(db.DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, nullable=False)


class LearningResource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    skill = db.Column(db.String(100), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    provider = db.Column(db.String(120), nullable=False, default="Self study")
    url = db.Column(db.String(500), nullable=False)
    difficulty = db.Column(db.String(32), nullable=False, default="Beginner")
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class JobCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(500), nullable=False, default="")
    jobs = db.relationship(
        "Job", secondary="job_category_job", back_populates="categories"
    )


class SkillDefinition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=_utcnow_naive, nullable=False)


job_category_job = db.Table(
    "job_category_job",
    db.Column("job_id", db.Integer, db.ForeignKey("job.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("job_category.id"), primary_key=True),
)


class InterviewQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False, default="General")
    question = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class InterviewPractice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False, index=True)
    questions = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow_naive, nullable=False)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(80), nullable=False, default="")
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, default=_utcnow_naive, nullable=False)


class HomepageFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    topic = db.Column(db.String(40), nullable=False)
    message = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, default=_utcnow_naive, nullable=False, index=True)
