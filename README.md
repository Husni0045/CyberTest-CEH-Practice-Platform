# CEH Practice Exam Website - Complete Case Study

## Overview
This is a professional CEH (Certified Ethical Hacker) practice examination platform built with Flask, MongoDB, and modern web technologies. The platform allows users to take randomized practice exams from different CEH versions and provides administrators with tools to manage the question database.

## Architecture & Technology Stack

### Backend
- **Flask** (Python web framework)
- **MongoDB Atlas** (cloud database for question storage)
- **Session-based authentication** (secure admin access)
- **Werkzeug password hashing** (PBKDF2 for admin credentials)

### Frontend  
- **Jinja2 templates** (server-side rendering)
- **Vanilla JavaScript** (interactive behaviors)
- **CSS3** (responsive design, professional styling)

### Security Features
- Password hashing with Werkzeug PBKDF2
- Secure session cookies (HttpOnly, SameSite, configurable lifetime)
- Rate limiting for login attempts (6 attempts per IP per 10 minutes)
- Server-side input validation and sanitization
- CSRF protection ready (can be enhanced with Flask-WTF)

## User Workflows

### 1. Regular User Flow (Taking Practice Exam)

#### Step 1: Landing Page
- User visits `http://127.0.0.1:5000`
- Sees professional hero layout with exam setup form
- Two main controls:
  - **Number of questions**: dropdown (25, 50, 75, 100, 125)
  - **CEH Version**: single-select radio buttons with toggle

#### Step 2: Version Selection
- User clicks "Select version" toggle button
- Version selector expands showing pills: "Version 12 — CEHv12", "Version 11 — CEHv11", etc.
- User selects one version (single-select enforced)
- "Start Exam" button becomes enabled
- Toggle button text updates to show selected version

#### Step 3: Starting Exam
- User clicks "Start Exam"
- Form posts to `/start_exam` with selected parameters
- Server queries MongoDB for questions matching the version
- Random sampling occurs (e.g., 50 random questions from Version 12)
- User is redirected to `/exam` page with question set

#### Step 4: Taking Exam
- Interactive exam interface with:
  - Question navigation sidebar
  - Current question display with multiple choice options
  - Progress tracking
  - Answer verification via AJAX calls to `/verify_answer`

#### Step 5: Results
- Real-time progress updates
- Final scoring and performance summary
- Option to restart or try different version

### 2. Administrator Workflow (Question Management)

#### Step 1: Admin Access
- Admin clicks "Admin" button on main page or in header
- Redirected to `/admin/login`
- Enters credentials:
  - Default: `admin` / `admin123`
  - Or environment-configured credentials

#### Step 2: Login Security
- System checks against rate limiting (max 6 attempts per IP per 10 minutes)
- Password verified against PBKDF2 hash
- On success: session established with 30-minute timeout
- Header navigation updates to show admin links

#### Step 3: Adding Questions
- Admin navigates to "Add Question" (automatically redirected after login)
- Professional form with validation:
  - **Version**: dropdown with "Version 12 — CEHv12" style labels
  - **Topic**: optional free text
  - **Question**: required textarea (minimum 10 characters)
  - **Options**: 4 input fields (minimum 2 required)
  - **Correct**: auto-populated select based on options entered

#### Step 4: Server-Side Validation
- Version must be in allowed list ["12", "11", "10", "9", "8"]
- Question text minimum length enforced
- At least 2 non-empty options required
- Correct answer must exactly match one option
- Duplicate prevention (same question text + version)
- Clean document creation with proper field types

#### Step 5: Viewing Questions
- Admin navigates to "View Questions" in header
- Table view showing all stored questions:
  - Document ID, Version, Question text, Options, Correct answer, Topic
  - Sorted by version (newest first)
  - Limited to 1000 records for performance

#### Step 6: Admin Session Management
- 30-minute session timeout
- Secure logout via "Logout" link
- Session cleared on logout

## Technical Implementation Details

### Database Schema
```javascript
// Question Document Structure
{
  "_id": "string_object_id",
  "version": "12",  // matches form values
  "question": "Which protocol is used to securely browse websites?",
  "options": ["HTTP", "FTP", "SSH", "HTTPS"],
  "correct": "HTTPS",  // exact match to one option
  "topic": "Network Security"  // optional
}
```

### Key Routes
- `GET /` - Main landing page
- `POST /start_exam` - Process exam parameters and start exam
- `POST /verify_answer` - AJAX endpoint for answer verification
- `GET /admin/login` - Admin login form
- `POST /admin/login` - Process admin authentication
- `GET /admin/add_question` - Question creation form
- `POST /admin/add_question` - Process new question
- `GET /admin/questions` - View all questions (admin only)
- `GET /admin/logout` - Clear admin session

### Security Implementation
```python
# Password Hashing
ADMIN_PASSWORD_HASH = generate_password_hash(raw_password)
if check_password_hash(ADMIN_PASSWORD_HASH, provided_password):
    # Login successful

# Rate Limiting
LOGIN_ATTEMPTS = {}  # IP -> [timestamp, timestamp, ...]
if len(attempts) >= LOGIN_MAX_ATTEMPTS:
    flash('Too many login attempts. Try again later.')

# Session Security
app.config.update({
    'SESSION_COOKIE_SECURE': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'PERMANENT_SESSION_LIFETIME': timedelta(minutes=30)
})
```

## Deployment Scenarios

### Development Environment
```powershell
# Set secure credentials
$env:CYBER_ADMIN_USER = "myadmin"
$env:CYBER_ADMIN_PASS = "SecurePass123"
$env:FLASK_SECRET_KEY = "dev-secret-key"

# Start development server
python .\app.py
```

### Production Environment
- Use HTTPS (SESSION_COOKIE_SECURE requires TLS)
- Set environment variables via secure methods (not command line)
- Consider Flask-Talisman for security headers
- Use process manager (gunicorn, uwsgi)
- Implement proper logging and monitoring
- Use Redis for distributed rate limiting

## Testing Scenarios

### Scenario 1: Basic Exam Flow
1. Visit homepage
2. Select "75 questions"
3. Choose "Version 12"
4. Verify "Start Exam" enables
5. Click start and confirm redirect to exam page
6. Answer questions and verify score calculation

### Scenario 2: Admin Question Management
1. Access admin login
2. Log in with correct credentials
3. Add a new question with all fields
4. Verify question appears in database
5. Start exam and confirm new question can appear
6. View questions list and confirm entry

### Scenario 3: Security Testing
1. Attempt login with wrong credentials 6+ times
2. Verify IP gets temporarily blocked
3. Test session timeout after 30 minutes
4. Verify admin routes redirect to login when not authenticated
5. Test duplicate question prevention

### Scenario 4: Validation Testing
1. Try to add question with invalid version
2. Test with empty question text
3. Test with only one option
4. Test with correct answer not matching options
5. Verify all show appropriate error messages

## Performance Considerations

### Database Queries
- Indexed on `version` field for fast filtering
- Random sampling uses MongoDB `$sample` aggregation
- Question list limited to 1000 documents
- Consider pagination for large datasets

### Frontend Optimization
- Cache-busting query parameters on static assets
- Responsive design for mobile devices
- Efficient DOM updates for exam interface
- Minimal JavaScript dependencies

### Scalability
- Stateless design (sessions in cookies)
- Database connection pooling
- Rate limiting prevents abuse
- Consider CDN for static assets in production

## Monitoring & Maintenance

### Key Metrics to Track
- Exam completion rates
- Question difficulty (answer accuracy)
- Admin login frequency
- Database query performance
- Error rates and response times

### Regular Maintenance
- Monitor question quality and user feedback
- Update CEH versions as new exams are released
- Review and rotate admin credentials
- Backup question database regularly
- Update dependencies for security patches

## Conclusion

This CEH practice exam platform provides a complete, secure, and professional solution for ethical hacking certification preparation. The architecture supports both end-user exam taking and administrative question management, with robust security measures and professional UI/UX design.

The system is production-ready with proper input validation, session management, and security controls, while remaining maintainable and extensible for future enhancements.