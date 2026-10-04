USE resume_ai;

INSERT INTO job(title,company,location,description,required_skills,min_experience) VALUES
('Junior Data Analyst','Insight Labs','Delhi',
'Analyze datasets, build dashboards, write SQL queries and create business reports using Python and Power BI.',
'python,sql,pandas,data analysis,power bi,excel',0),

('Machine Learning Intern','Nova AI','Remote',
'Build machine learning models, preprocess data, evaluate models and experiment with NLP and deep learning.',
'python,pandas,numpy,scikit-learn,machine learning,nlp,deep learning',0),

('Backend Developer','TechForge','Bengaluru',
'Develop REST APIs and backend services using Python, Flask, SQL and Git. Work with databases and testing.',
'python,flask,sql,rest api,git,mysql',1),

('Frontend Developer','PixelStack','Gurugram',
'Build responsive interfaces using HTML, CSS and JavaScript. React knowledge is preferred.',
'html,css,javascript,react,git',0),

('AI Engineer','VisionNext','Hyderabad',
'Work on NLP, computer vision and deep learning systems using Python and modern ML frameworks.',
'python,machine learning,deep learning,nlp,computer vision,tensorflow,pytorch',1);

INSERT INTO user(name,email,password_hash,role)
VALUES ('System Admin','admin@resumeai.local',
'scrypt:32768:8:1$GCTzYnaETZro96S4$955b5446c144f2d36fe19804e4d399e0f9991d362c6d6d7c49928d7117b5174b8cad1a2be44db6fa3f8e3de79ef60102fdf89891f4c3ae49dd9705f102c42ce2','admin');
