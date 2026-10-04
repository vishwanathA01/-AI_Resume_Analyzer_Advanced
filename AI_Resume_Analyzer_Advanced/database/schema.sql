CREATE DATABASE IF NOT EXISTS resume_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE resume_ai;

CREATE TABLE user (
 id INT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(120) NOT NULL,
 email VARCHAR(180) UNIQUE NOT NULL,
 password_hash VARCHAR(255) NOT NULL,
 role VARCHAR(20) DEFAULT 'user',
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE profile_picture (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL UNIQUE,
 filename VARCHAR(80) NOT NULL UNIQUE,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE community_post (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL,
 body VARCHAR(1200) NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX ix_community_post_user_id (user_id),
 INDEX ix_community_post_created_at (created_at),
 FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE community_comment (
 id INT AUTO_INCREMENT PRIMARY KEY,
 post_id INT NOT NULL,
 user_id INT NOT NULL,
 body VARCHAR(600) NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX ix_community_comment_post_id (post_id),
 INDEX ix_community_comment_user_id (user_id),
 INDEX ix_community_comment_created_at (created_at),
 FOREIGN KEY(post_id) REFERENCES community_post(id) ON DELETE CASCADE,
 FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE community_like (
 id INT AUTO_INCREMENT PRIMARY KEY,
 post_id INT NOT NULL,
 user_id INT NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY uq_community_like_post_user (post_id, user_id),
 INDEX ix_community_like_post_id (post_id),
 INDEX ix_community_like_user_id (user_id),
 FOREIGN KEY(post_id) REFERENCES community_post(id) ON DELETE CASCADE,
 FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE resume (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL,
 filename VARCHAR(255) NOT NULL,
 extracted_text LONGTEXT,
 resume_score FLOAT DEFAULT 0,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE job (
 id INT AUTO_INCREMENT PRIMARY KEY,
 title VARCHAR(180) NOT NULL,
 company VARCHAR(180) NOT NULL,
 location VARCHAR(180) DEFAULT 'Remote',
 description LONGTEXT NOT NULL,
 required_skills TEXT,
 min_experience FLOAT DEFAULT 0,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE match (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL,
 resume_id INT NOT NULL,
 job_id INT NOT NULL,
 similarity_score FLOAT DEFAULT 0,
 skill_score FLOAT DEFAULT 0,
 final_score FLOAT DEFAULT 0,
 missing_skills TEXT,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE,
 FOREIGN KEY(resume_id) REFERENCES resume(id) ON DELETE CASCADE,
 FOREIGN KEY(job_id) REFERENCES job(id) ON DELETE CASCADE
);

CREATE TABLE saved_job (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL,
 job_id INT NOT NULL,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY uq_saved_job_user_job (user_id, job_id),
 FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE,
 FOREIGN KEY(job_id) REFERENCES job(id) ON DELETE CASCADE
);

CREATE TABLE application (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL,
 job_id INT NOT NULL,
 status VARCHAR(32) NOT NULL DEFAULT 'Interested',
 notes TEXT NOT NULL,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE,
 FOREIGN KEY(job_id) REFERENCES job(id) ON DELETE CASCADE
);

CREATE TABLE notification (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL,
 title VARCHAR(180) NOT NULL,
 message TEXT NOT NULL,
 category VARCHAR(32) NOT NULL DEFAULT 'general',
 is_read BOOLEAN NOT NULL DEFAULT FALSE,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE user_settings (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL UNIQUE,
 preferred_location VARCHAR(180) NOT NULL DEFAULT '',
 email_notifications BOOLEAN NOT NULL DEFAULT TRUE,
 updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE learning_resource (
 id INT AUTO_INCREMENT PRIMARY KEY,
 skill VARCHAR(100) NOT NULL,
 title VARCHAR(180) NOT NULL,
 provider VARCHAR(120) NOT NULL DEFAULT 'Self study',
 url VARCHAR(500) NOT NULL,
 difficulty VARCHAR(32) NOT NULL DEFAULT 'Beginner',
 is_active BOOLEAN NOT NULL DEFAULT TRUE,
 INDEX ix_learning_resource_skill (skill)
);

CREATE TABLE job_category (
 id INT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(100) NOT NULL UNIQUE,
 description VARCHAR(500) NOT NULL DEFAULT ''
);

CREATE TABLE job_category_job (
 job_id INT NOT NULL,
 category_id INT NOT NULL,
 PRIMARY KEY(job_id, category_id),
 FOREIGN KEY(job_id) REFERENCES job(id) ON DELETE CASCADE,
 FOREIGN KEY(category_id) REFERENCES job_category(id) ON DELETE CASCADE
);

CREATE TABLE skill_definition (
 id INT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(100) NOT NULL UNIQUE,
 is_active BOOLEAN NOT NULL DEFAULT TRUE,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE interview_question (
 id INT AUTO_INCREMENT PRIMARY KEY,
 category VARCHAR(100) NOT NULL DEFAULT 'General',
 question TEXT NOT NULL,
 is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE interview_practice (
 id INT AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL,
 job_id INT NOT NULL,
 questions JSON NOT NULL,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 INDEX ix_interview_practice_user_id (user_id),
 INDEX ix_interview_practice_job_id (job_id),
 FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE,
 FOREIGN KEY(job_id) REFERENCES job(id) ON DELETE CASCADE
);

CREATE TABLE audit_log (
 id INT AUTO_INCREMENT PRIMARY KEY,
 actor_id INT NULL,
 action VARCHAR(100) NOT NULL,
 target_type VARCHAR(80) NOT NULL DEFAULT '',
 target_id INT NULL,
 details TEXT NOT NULL,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 INDEX ix_audit_log_actor_id (actor_id),
 FOREIGN KEY(actor_id) REFERENCES user(id) ON DELETE SET NULL
);

CREATE TABLE homepage_feedback (
 id INT AUTO_INCREMENT PRIMARY KEY,
 rating INT NOT NULL,
 topic VARCHAR(40) NOT NULL,
 message TEXT NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX ix_homepage_feedback_created_at (created_at)
);
