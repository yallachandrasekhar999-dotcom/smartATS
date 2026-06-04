import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Weak vs Strong Action Verbs dictionary
ACTION_VERB_SUGGESTIONS = {
    'helped': 'Assisted, Supported, Facilitated, Collaborated, Contributed',
    'managed': 'Spearheaded, Orchestrated, Coordinated, Directed, Guided',
    'led': 'Chaired, Pioneered, Executed, Headed, Spearheaded',
    'worked on': 'Engineered, Constructed, Developed, Authored, Formulated',
    'did': 'Implemented, Completed, Executed, Accomplished, Produced',
    'made': 'Designed, Formulated, Developed, Standardized, Concocted',
    'responsible for': 'Accountable for, Entrusted with, Delegated to, Spearheaded',
    'created': 'Engineered, Authored, Devised, Established, Incubated',
    'improved': 'Streamlined, Optimized, Boosted, Amplified, Enhanced',
    'used': 'Leveraged, Deployed, Utilized, Harness, Adopted'
}

# Industry recommended skills mapping for learning paths
SKILL_LEARNING_RECOMMENDATIONS = {
    'Python': ['Django', 'FastAPI', 'Pandas', 'Data Structures & Algorithms'],
    'React.js': ['Redux Toolkit', 'Next.js', 'TypeScript', 'Tailwind CSS'],
    'JavaScript': ['React.js', 'Node.js', 'TypeScript', 'ES6+ Features'],
    'SQL': ['PostgreSQL', 'Database Indexing', 'ORM (SQLAlchemy/Sequelize)', 'NoSQL'],
    'Docker': ['Kubernetes', 'CI/CD Pipelines (GitHub Actions)', 'Terraform', 'AWS EC2'],
    'AWS': ['Docker', 'Terraform', 'AWS Lambda (Serverless)', 'CloudFormation'],
    'Machine Learning': ['Deep Learning', 'PyTorch', 'TensorFlow', 'MLOps (MLflow)'],
    'Java': ['Spring Boot', 'Hibernate', 'Microservices Architecture', 'Docker'],
    'Node.js': ['Express.js', 'NestJS', 'MongoDB', 'Redis Caching'],
    'Data Science': ['Machine Learning', 'Data Visualization (Tableau)', 'Big Data (Spark)']
}

def calculate_ats_score(resume_data, jd_data):
    """
    Computes an ATS score based on:
    1. Skill Match (60%)
    2. JD Keyword Match (20%)
    3. Structural Checks (10%)
    4. Contact / Details Check (10%)
    """
    resume_skills = set(s.lower() for s in resume_data.get('skills', []))
    jd_skills = set(s.lower() for s in jd_data.get('skills', []))
    
    # 1. Skill Match (60%)
    skill_score = 0.0
    matched_skills = []
    missing_skills = []
    
    if jd_skills:
        matched_set = resume_skills.intersection(jd_skills)
        missing_set = jd_skills.difference(resume_skills)
        
        # Map back to display casing from jd_data or resume_data
        display_map = {s.lower(): s for s in jd_data.get('skills', [])}
        for s in resume_data.get('skills', []):
            display_map[s.lower()] = s
            
        matched_skills = [display_map[s] for s in matched_set]
        missing_skills = [display_map[s] for s in missing_set]
        
        skill_score = (len(matched_set) / len(jd_skills)) * 60.0
    else:
        # If no skills are defined in JD, give default base score or compare against general skills
        skill_score = 45.0 # Base mark
        
    # 2. General Keyword Match (20%)
    # Tokenize and check overlapping words, removing stopwords and punctuation
    keyword_score = 0.0
    try:
        stop_words = set(stopwords.words('english'))
    except:
        stop_words = set()
        
    resume_text = resume_data.get('raw_text', '').lower()
    jd_text = jd_data.get('raw_text', '').lower()
    
    # Tokenize
    resume_words = set(re.findall(r'\b[a-z]{3,}\b', resume_text))
    jd_words = set(re.findall(r'\b[a-z]{3,}\b', jd_text))
    
    # Filter stopwords and skills
    resume_keywords = resume_words.difference(stop_words).difference(resume_skills)
    jd_keywords = jd_words.difference(stop_words).difference(jd_skills)
    
    if jd_keywords:
        matched_kw_set = resume_keywords.intersection(jd_keywords)
        keyword_score = (len(matched_kw_set) / len(jd_keywords)) * 20.0
        # Cap keyword score in case
        keyword_score = min(keyword_score, 20.0)
    else:
        keyword_score = 15.0
        
    # 3. Structural Checks (10%)
    # Has Experience (5%), Has Education (5%)
    struct_score = 0.0
    if len(resume_data.get('experience', [])) > 0:
        struct_score += 5.0
    if len(resume_data.get('education', [])) > 0:
        struct_score += 5.0
        
    # 4. Contact / Details Check (10%)
    # Has Email (3%), Has Phone (3%), Has Name (4%)
    contact_score = 0.0
    if resume_data.get('email'):
        contact_score += 3.0
    if resume_data.get('phone'):
        contact_score += 3.0
    if resume_data.get('name') and resume_data.get('name') != "Candidate Name Not Found":
        contact_score += 4.0
        
    # Aggregate ATS Score
    total_score = skill_score + keyword_score + struct_score + contact_score
    total_score = round(min(total_score, 100.0), 1)
    
    # Categorization
    if total_score >= 90.0:
        category = 'Excellent'
    elif total_score >= 75.0:
        category = 'Good'
    elif total_score >= 50.0:
        category = 'Average'
    else:
        category = 'Needs Improvement'
        
    return {
        'score': total_score,
        'category': category,
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
        'breakdown': {
            'skills': round(skill_score, 1),
            'keywords': round(keyword_score, 1),
            'structure': round(struct_score, 1),
            'contact': round(contact_score, 1)
        }
    }


def analyze_resume_suggestions(resume_data):
    """
    Generates action verb replacements, section quality issues, and optimizations.
    """
    raw_text = resume_data.get('raw_text', '').lower()
    suggestions = {
        'verb_replacements': [],
        'weak_sections': [],
        'improvements': []
    }
    
    # 1. Action verb suggestions
    for weak_verb, strong_alternatives in ACTION_VERB_SUGGESTIONS.items():
        # Match using word boundaries
        pattern = r'\b' + re.escape(weak_verb) + r'\b'
        if re.search(pattern, raw_text):
            suggestions['verb_replacements'].append({
                'weak': weak_verb,
                'suggested': strong_alternatives
            })
            
    # 2. Section Checks
    if not resume_data.get('experience'):
        suggestions['weak_sections'].append({
            'section': 'Work Experience',
            'severity': 'High',
            'reason': 'No explicit work experience section parsed. Ensure headings like "Professional Experience" are clearly styled.'
        })
    elif len(resume_data.get('experience')) < 3:
        suggestions['weak_sections'].append({
            'section': 'Work Experience',
            'severity': 'Medium',
            'reason': 'Your experience section is very brief. Provide 3-4 bullet points per job detailing quantified achievements.'
        })
        
    if not resume_data.get('certifications'):
        suggestions['weak_sections'].append({
            'section': 'Certifications',
            'severity': 'Low',
            'reason': 'No certifications section detected. Adding relevant technical certifications increases ATS ranking.'
        })
        
    if not resume_data.get('phone') or not resume_data.get('email'):
        suggestions['weak_sections'].append({
            'section': 'Contact Details',
            'severity': 'High',
            'reason': 'Missing email or phone number. Recruiters cannot reach out if key contact details are omitted or un-parseable.'
        })
        
    # 3. Keyword/General optimizations
    # Suggest specific learning path based on parsed skills
    skills_learned = [s.title() for s in resume_data.get('skills', [])]
    learning_recommendations = []
    
    count = 0
    for skill_name in skills_learned:
        if count >= 3:
            break
        # Match with recommended list
        for dict_skill, recommendations in SKILL_LEARNING_RECOMMENDATIONS.items():
            if skill_name.lower() == dict_skill.lower():
                learning_recommendations.extend(recommendations)
                count += 1
                
    learning_recommendations = list(set(learning_recommendations))
    
    suggestions['improvements'] = [
        "Include metrics and quantified results (e.g. 'Improved speed by 30%', 'Managed $5K budget') to demonstrate real impact.",
        "Ensure your resume file is in PDF format with selectable text, rather than an image-only PDF.",
        "Organize your skills in a clear grid/table categorized by Languages, Frameworks, and Tools."
    ]
    
    if learning_recommendations:
        suggestions['learning_path'] = learning_recommendations[:4]
    else:
        suggestions['learning_path'] = ['Git & GitHub', 'Agile Methodologies', 'Docker Containers', 'REST API Design']
        
    return suggestions


def recommend_jobs(user_skills, job_postings):
    """
    Ranks standard jobs from database based on skills matching percentage.
    """
    recommendations = []
    user_skills_set = set(s.lower() for s in user_skills)
    
    for job in job_postings:
        job_skills = set(s.lower() for s in job.skills_required)
        if not job_skills:
            continue
            
        matched = user_skills_set.intersection(job_skills)
        match_percentage = (len(matched) / len(job_skills)) * 100
        
        recommendations.append({
            'job_id': job.id,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'match_score': round(match_percentage, 1),
            'matched_skills': [s.title() for s in matched],
            'missing_skills': [s.title() for s in job_skills.difference(user_skills_set)],
            'description': job.description,
            'url': job.url
        })
        
    # Sort by match score descending
    recommendations = sorted(recommendations, key=lambda x: x['match_score'], reverse=True)
    return recommendations


def generate_alignment_advice(matched_skills, missing_skills, weak_sections):
    """
    Compiles detailed strategy guides, section corrections, and bullet point refactoring
    advices based on what is missing to secure a job match.
    """
    advice_items = []
    
    # 1. Critical Missing Skills integration tips
    if missing_skills:
        skills_subset = missing_skills[:4]
        skills_str = ", ".join(skills_subset)
        advice_items.append({
            'title': 'Integrate Missing Critical Skills',
            'icon': 'fa-lightbulb',
            'color': 'text-amber-400',
            'explanation': f"The job description highlights requirements for: <b>{skills_str}</b>. Add these keywords to your main 'Skills' section. Furthermore, describe a past project or course where you used these tools to ensure the ATS scores them."
        })
        
        # Rewrite bullet points formatting examples
        refactor_examples = []
        for skill in missing_skills[:3]:
            refactor_examples.append(f"<li class='ml-4 list-disc mt-1'>\"Leveraged <b>{skill}</b> to implement backend features and optimize code efficiency by 15%.\"</li>")
            
        advice_items.append({
            'title': 'Refactoring Examples (Add to Work Experience)',
            'icon': 'fa-pen-to-square',
            'color': 'text-indigo-400',
            'explanation': "Transform experience descriptions to incorporate these tools naturally. Try using phrasing like:<ul class='mt-1 text-slate-400 font-mono text-[11px]'>" + "".join(refactor_examples) + "</ul>"
        })
        
    # 2. Section formatting & structure
    if weak_sections:
        sections_str = ", ".join([s['section'] for s in weak_sections])
        advice_items.append({
            'title': 'Structure Heading Formats',
            'icon': 'fa-folder-plus',
            'color': 'text-rose-400',
            'explanation': f"Hiring ATS engines look for distinct headings. Your resume appears to have weak descriptors for: <b>{sections_str}</b>. Create a clear bold header (e.g. 'Certifications' or 'Work Experience') to ensure parsing succeeds."
        })
    else:
        advice_items.append({
            'title': 'Parser Integrity Checklist',
            'icon': 'fa-circle-check',
            'color': 'text-emerald-400',
            'explanation': "Excellent layout integrity. Key document structures (Experience, Education, Contact) are clearly demarcated, enabling clean parsing."
        })

    # 3. Strategy / Tips to get that job
    strategy_bullets = []
    if matched_skills:
        best_skill = matched_skills[0]
        strategy_bullets.append(f"<li class='ml-4 list-disc mt-1'><b>Leverage matched skills</b>: Double-down on your experience with <b>{best_skill}</b> in interviews. Tell stories showing quantified achievements.</li>")
    if missing_skills:
        missing_skill = missing_skills[0]
        strategy_bullets.append(f"<li class='ml-4 list-disc mt-1'><b>Address skill gaps</b>: Proactively spend a weekend building a small sandbox project using <b>{missing_skill}</b> and add it to your portfolio to secure the role.</li>")
    else:
        strategy_bullets.append("<li class='ml-4 list-disc mt-1'><b>Stand out</b>: Since you match all core skills, focus on adding numeric metrics (budget size, performance speeds) to outrank other applicants.</li>")
        
    advice_items.append({
        'title': 'How to Get This Job - Strategic Roadmap',
        'icon': 'fa-play-circle',
        'color': 'text-emerald-400',
        'explanation': f"Follow this advice to secure the interview:<ul class='mt-1 space-y-1'>" + "".join(strategy_bullets) + "</ul>"
    })
    
    return advice_items

