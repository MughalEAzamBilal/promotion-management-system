/**
 * Qualifications Dynamic Selector
 * Loads predefined degrees, levels, and subjects according to SED policies.
 */

const SED_QUALIFICATIONS_CATALOG = {
  "Matric": {
    "is_professional": false,
    "degrees": [
      {
        "name": "SSC (Science - Biology)",
        "subjects": ["Biology", "Chemistry", "Physics", "Mathematics", "English", "Urdu", "Islamiyat", "Pakistan Studies", "Electrical Wiring"]
      },
      {
        "name": "SSC (Science - Computer Science)",
        "subjects": ["Computer Science", "Physics", "Chemistry", "Mathematics", "English", "Urdu", "Islamiyat", "Pakistan Studies", "Electrical Wiring"]
      },
      {
        "name": "SSC (Science / Technical - Electrical Wiring)",
        "subjects": ["Electrical Wiring", "Physics", "Chemistry", "Mathematics", "English", "Urdu", "Islamiyat", "Pakistan Studies"]
      },
      {
        "name": "SSC (Arts / Humanities)",
        "subjects": ["General Science", "General Mathematics", "English", "Urdu", "Islamiyat", "Pakistan Studies", "Civics", "Education"]
      },
      {
        "name": "Sanvia Aama (Dars-e-Nizami)",
        "subjects": ["Arabic", "Quran", "Hadith", "Fiqh", "Islamic History"]
      }
    ]
  },
  "Intermediate": {
    "is_professional": false,
    "degrees": [
      {
        "name": "F.Sc (Pre-Medical)",
        "subjects": ["Biology", "Physics", "Chemistry", "English", "Urdu", "Islamic Studies", "Pakistan Studies"]
      },
      {
        "name": "F.Sc (Pre-Engineering)",
        "subjects": ["Mathematics", "Physics", "Chemistry", "English", "Urdu", "Islamic Studies", "Pakistan Studies"]
      },
      {
        "name": "ICS (Computer Science & Physics)",
        "subjects": ["Computer Science", "Mathematics", "Physics", "English", "Urdu"]
      },
      {
        "name": "ICS (Computer Science & Statistics)",
        "subjects": ["Computer Science", "Mathematics", "Statistics", "English", "Urdu"]
      },
      {
        "name": "ICS (Computer Science & Economics)",
        "subjects": ["Computer Science", "Mathematics", "Economics", "English", "Urdu"]
      },
      {
        "name": "F.A (Humanities / Arts)",
        "subjects": ["English Literature", "Urdu Literature", "Islamic Studies", "History", "Civics", "Education", "Sociology", "Arabic", "Punjabi"]
      },
      {
        "name": "I.Com",
        "subjects": ["Accounting", "Principles of Commerce", "Business Math & Statistics", "Economics"]
      },
      {
        "name": "Sanvia Khasa (Dars-e-Nizami)",
        "subjects": ["Arabic Grammar", "Tafseer", "Fiqh", "Islamic Jurisprudence"]
      }
    ]
  },
  "Bachelor": {
    "is_professional": false,
    "degrees": [
      {
        "name": "B.Sc (Double Math & Physics)",
        "subjects": ["Mathematics A", "Mathematics B", "Physics", "English"]
      },
      {
        "name": "B.Sc (Physics, Chemistry, Math)",
        "subjects": ["Physics", "Chemistry", "Mathematics", "English"]
      },
      {
        "name": "B.Sc (Botany, Zoology, Chemistry)",
        "subjects": ["Botany", "Zoology", "Chemistry", "English"]
      },
      {
        "name": "B.Sc (Computer Studies, Math, Stats)",
        "subjects": ["Computer Studies", "Mathematics", "Statistics"]
      },
      {
        "name": "B.A (Humanities / Social Sciences)",
        "subjects": ["English (Compulsory)", "Urdu", "Islamic Studies", "Political Science", "History", "Economics", "Education", "Sociology", "Arabic", "Punjabi"]
      },
      {
        "name": "B.Com",
        "subjects": ["Commerce", "Financial Accounting", "Cost Accounting", "Business Law", "Economics"]
      },
      {
        "name": "Shahadat-ul-Aliya",
        "subjects": ["Arabic", "Islamic Shariah", "Hadith", "Tafseer"]
      }
    ]
  },
  "BS-4Years": {
    "is_professional": false,
    "degrees": [
      {
        "name": "BS Mathematics",
        "subjects": ["Mathematics", "Pure Mathematics", "Applied Mathematics", "Calculus", "Algebra"]
      },
      {
        "name": "BS Physics",
        "subjects": ["Physics", "Quantum Mechanics", "Electromagnetism", "Solid State Physics", "Electronics"]
      },
      {
        "name": "BS Chemistry",
        "subjects": ["Chemistry", "Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry", "Biochemistry"]
      },
      {
        "name": "BS Botany",
        "subjects": ["Botany", "Plant Anatomy", "Plant Taxonomy", "Genetics", "Physiology"]
      },
      {
        "name": "BS Zoology",
        "subjects": ["Zoology", "Animal Diversity", "Physiology", "Molecular Biology", "Ecology"]
      },
      {
        "name": "BS Biology",
        "subjects": ["Biology", "Cell Biology", "Genetics", "Microbiology", "Biotechnology"]
      },
      {
        "name": "BS Computer Science (BSCS)",
        "subjects": ["Computer Science", "Programming", "Data Structures", "Database Systems", "Software Engineering"]
      },
      {
        "name": "BS Information Technology (BSIT)",
        "subjects": ["Information Technology", "Networking", "Web Systems", "Database Administration"]
      },
      {
        "name": "BS English (Literature & Linguistics)",
        "subjects": ["English Literature", "Applied Linguistics", "Classical Poetry", "Drama", "Modern Novel"]
      },
      {
        "name": "BS Urdu",
        "subjects": ["Urdu Literature", "Classical Poetry", "Urdu Prose", "Literary Criticism", "Iqbaliyat"]
      },
      {
        "name": "BS Islamic Studies",
        "subjects": ["Islamic Studies", "Quranic Studies", "Hadith", "Islamic Jurisprudence (Fiqh)", "Seerat-un-Nabi"]
      },
      {
        "name": "BS Pakistan Studies",
        "subjects": ["Pakistan Studies", "Pakistan Movement", "Constitutional History", "Geography of Pakistan"]
      },
      {
        "name": "BS History",
        "subjects": ["History", "History of Subcontinent", "Islamic History", "Modern World History"]
      },
      {
        "name": "BS Political Science",
        "subjects": ["Political Science", "Political Theory", "International Relations", "Comparative Politics"]
      },
      {
        "name": "BS Economics",
        "subjects": ["Economics", "Microeconomics", "Macroeconomics", "Development Economics", "Econometrics"]
      },
      {
        "name": "BS Statistics",
        "subjects": ["Statistics", "Probability Theory", "Statistical Inference", "Sampling Techniques"]
      },
      {
        "name": "BS Arabic",
        "subjects": ["Arabic Literature", "Arabic Grammar", "Translation Studies", "Islamic Texts"]
      },
      {
        "name": "BS Physical Education & Sports Sciences",
        "subjects": ["Physical Education", "Sports Coaching", "Kinesiology", "Exercise Physiology", "Sports Management"]
      }
    ]
  },
  "Master": {
    "is_professional": false,
    "degrees": [
      {
        "name": "M.Sc Mathematics",
        "subjects": ["Mathematics", "Real Analysis", "Complex Analysis", "Modern Algebra", "Topology"]
      },
      {
        "name": "M.Sc Physics",
        "subjects": ["Physics", "Nuclear Physics", "Solid State Physics", "Electrodynamics", "Quantum Physics"]
      },
      {
        "name": "M.Sc Chemistry",
        "subjects": ["Chemistry", "Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry", "Analytical Chemistry"]
      },
      {
        "name": "M.Sc Botany",
        "subjects": ["Botany", "Plant Ecology", "Plant Physiology", "Plant Genetics", "Morphology"]
      },
      {
        "name": "M.Sc Zoology",
        "subjects": ["Zoology", "Cell Biology", "Endocrinology", "Genetics", "Fisheries & Wildlife"]
      },
      {
        "name": "M.Sc Computer Science / MCS / MIT",
        "subjects": ["Computer Science", "Artificial Intelligence", "Computer Networks", "Database Management"]
      },
      {
        "name": "M.Sc Statistics",
        "subjects": ["Statistics", "Probability", "Multivariate Analysis", "Regression Analysis", "Design of Experiments"]
      },
      {
        "name": "M.A English",
        "subjects": ["English Literature", "Linguistics", "Literary Criticism", "Drama & Poetry"]
      },
      {
        "name": "M.A Urdu",
        "subjects": ["Urdu Literature", "Urdu Prose", "Poetry & Criticism", "Research Methodology"]
      },
      {
        "name": "M.A Islamic Studies",
        "subjects": ["Islamic Studies", "Quran", "Hadith", "Islamic Law", "Comparative Religions"]
      },
      {
        "name": "M.A Pakistan Studies",
        "subjects": ["Pakistan Studies", "History of Pakistan", "Foreign Policy of Pakistan", "Political Dynamics"]
      },
      {
        "name": "M.A History",
        "subjects": ["Indo-Pak History", "Islamic History", "World Civilizations", "Research in History"]
      },
      {
        "name": "M.A Political Science",
        "subjects": ["Political Systems", "Public Administration", "International Law", "Diplomacy"]
      },
      {
        "name": "M.A Economics",
        "subjects": ["Macroeconomics", "Monetary Economics", "Public Finance", "International Trade"]
      },
      {
        "name": "M.A Arabic",
        "subjects": ["Arabic Literature", "Classical Texts", "Arabic Linguistics", "Balaghat & Urood"]
      },
      {
        "name": "Shahadat-ul-Almia",
        "subjects": ["Higher Arabic", "Quranic Sciences", "Hadith Sciences", "Fiqh & Usool-ul-Fiqh"]
      }
    ]
  },
  "Professional Teaching": {
    "is_professional": true,
    "degrees": [
      {
        "name": "B.Ed (1.5 Years)",
        "subjects": ["Educational Leadership", "Research Methods in Education", "Pedagogy", "Curriculum & Instruction", "Educational Assessment"]
      },
      {
        "name": "B.Ed (2.5 Years)",
        "subjects": ["Secondary Teacher Education", "Subject Pedagogy", "Measurement & Evaluation", "Guidance & Counseling"]
      },
      {
        "name": "B.Ed (4-Year Honors)",
        "subjects": ["Elementary Education", "General Pedagogy", "Subject Specific Teaching Methods", "Teaching Practicum", "Classroom Assessment"]
      },
      {
        "name": "ADE (Associate Degree in Education - 2 Years)",
        "subjects": ["Teaching of English", "Teaching of Mathematics", "Teaching of Science", "Classroom Management", "Child Development"]
      },
      {
        "name": "B.S.Ed (Bachelor of Science in Education)",
        "subjects": ["Teaching of Physical Sciences", "Teaching of Biological Sciences", "Mathematics Pedagogy", "Science Curriculum"]
      },
      {
        "name": "M.Ed (Master of Education)",
        "subjects": ["Teacher Education", "Educational Administration & Management", "Curriculum Studies", "Comparative Education"]
      },
      {
        "name": "M.A Education",
        "subjects": ["Foundations of Education", "Educational Planning & Financing", "Philosophy of Education", "Educational Psychology"]
      },
      {
        "name": "Diploma in Physical Education (DPE)",
        "subjects": ["Physical Education", "Athletics", "Gymnastics", "Rules of Games & Sports", "Sports Physiology"]
      },
      {
        "name": "ATTC (Arabic Teacher Training Certificate)",
        "subjects": ["Arabic Teaching Methodology", "Tajweed & Qirat", "Quranic Phonetics", "Arabic Grammar Teaching"]
      },
      {
        "name": "Junior Drawing Master / Art Diploma (DM)",
        "subjects": ["Fine Arts", "Technical Drawing", "Perspective Drawing", "Model Drawing", "Calligraphy"]
      },
      {
        "name": "CT (Certificate of Teaching - Historical)",
        "subjects": ["Teaching of General Science", "Teaching of Mathematics", "Teaching of English", "School Administration"]
      },
      {
        "name": "PTC (Primary Teaching Certificate - Historical)",
        "subjects": ["Primary School Pedagogy", "Child Psychology", "Basic Mathematics Teaching", "Urdu Language Teaching"]
      }
    ]
  },
  "M.Phil": {
    "is_professional": false,
    "degrees": [
      {
        "name": "M.Phil Education",
        "subjects": ["Advanced Research Methods", "Educational Assessment & Evaluation", "Educational Policy & Planning", "Curriculum Design"]
      },
      {
        "name": "M.Phil Mathematics",
        "subjects": ["Fluid Dynamics", "Graph Theory", "Number Theory", "Numerical Analysis"]
      },
      {
        "name": "M.Phil Physics",
        "subjects": ["Condensed Matter Physics", "Nanotechnology", "Plasma Physics", "Laser Physics"]
      },
      {
        "name": "M.Phil Chemistry",
        "subjects": ["Synthetic Organic Chemistry", "Coordination Chemistry", "Catalysis", "Environmental Chemistry"]
      },
      {
        "name": "M.Phil English",
        "subjects": ["Postcolonial Literature", "Critical Discourse Analysis", "Sociolinguistics", "Modern Literary Theory"]
      },
      {
        "name": "M.Phil Urdu",
        "subjects": ["Tahqeeq-o-Tanqeed", "Classical Poetry Research", "Modern Urdu Fiction"]
      },
      {
        "name": "M.Phil Islamic Studies",
        "subjects": ["Modern Jurisprudence Issues", "Islamic Economics", "Contemporary Muslim Thought"]
      },
      {
        "name": "M.Phil Computer Science",
        "subjects": ["Artificial Intelligence", "Machine Learning", "Advanced Algorithms", "Computer Networks", "Data Science", "Software Engineering"]
      },
      {
        "name": "M.Phil Information Technology",
        "subjects": ["Information Security", "Enterprise Systems", "Cloud Computing", "Database Systems", "IT Management", "Web Technologies"]
      },
      {
        "name": "M.Phil Pakistan Studies",
        "subjects": ["Governance & Politics", "Socio-Economic Development", "Foreign Relations"]
      }
    ]
  },
  "PhD": {
    "is_professional": false,
    "degrees": [
      {
        "name": "Ph.D in Education",
        "subjects": ["Higher Education Studies", "Educational Policy Formulation", "Doctoral Research Dissertation"]
      },
      {
        "name": "Ph.D in Computer Science",
        "subjects": ["Doctoral Research in Computer Science", "Deep Learning & Neural Networks", "Advanced Data Science", "Distributed Computing"]
      },
      {
        "name": "Ph.D in Information Technology",
        "subjects": ["Doctoral Research in IT", "Cybersecurity & Governance", "Information Systems Architecture", "Big Data Analytics"]
      },
      {
        "name": "Ph.D in Relevant School Subject",
        "subjects": ["Advanced Doctoral Research & Dissertation", "Specialized Subject Research"]
      }
    ]
  }
};

const PREDEFINED_BOARDS_UNIVERSITIES = [
  "University of the Punjab (PU), Lahore",
  "University of Education (UE), Lahore",
  "Allama Iqbal Open University (AIOU), Islamabad",
  "Bahauddin Zakariya University (BZU), Multan",
  "Government College University (GCU), Lahore",
  "University of Agriculture (UAF), Faisalabad",
  "Government College University (GCUF), Faisalabad",
  "Islamia University of Bahawalpur (IUB)",
  "University of Gujrat (UOG)",
  "University of Sargodha (UOS)",
  "Lahore College for Women University (LCWU)",
  "University of Engineering & Technology (UET), Lahore",
  "Pir Mehr Ali Shah Arid Agriculture University, Rawalpindi",
  "BISE Lahore",
  "BISE Gujranwala",
  "BISE Rawalpindi",
  "BISE Faisalabad",
  "BISE Multan",
  "BISE Sahiwal",
  "BISE Sargodha",
  "BISE Bahawalpur",
  "BISE Dera Ghazi Khan",
  "Federal Board of Intermediate & Secondary Education (FBISE), Islamabad",
  "Wifaq-ul-Madaris Al-Arabia Pakistan"
];

function initQualificationsSelector(prefix) {
  const levelSelect = document.getElementById(`${prefix}_degree_level`);
  const titleSelect = document.getElementById(`${prefix}_degree_select`);
  const customTitleInput = document.getElementById(`${prefix}_degree_name`);
  const customTitleContainer = document.getElementById(`${prefix}_custom_title_container`);
  const subjectsContainer = document.getElementById(`${prefix}_subjects_checkboxes`);
  const subjectInput = document.getElementById(`${prefix}_subject`);
  const profCheckbox = document.getElementById(`${prefix}_is_prof`);
  const instituteDatalist = document.getElementById(`${prefix}_institutes_list`);

  if (!levelSelect || !titleSelect) return;

  // Populate Institutes Datalist
  if (instituteDatalist && instituteDatalist.children.length === 0) {
    PREDEFINED_BOARDS_UNIVERSITIES.forEach(inst => {
      const opt = document.createElement('option');
      opt.value = inst;
      instituteDatalist.appendChild(opt);
    });
  }

  // Handle Level Change
  function updateDegreeTitles() {
    const selectedLevel = levelSelect.value;
    const cat = SED_QUALIFICATIONS_CATALOG[selectedLevel];
    titleSelect.innerHTML = '<option value="">-- Select Predefined Degree --</option>';

    if (cat) {
      if (profCheckbox) {
        profCheckbox.checked = !!cat.is_professional;
      }
      cat.degrees.forEach(deg => {
        const opt = document.createElement('option');
        opt.value = deg.name;
        opt.textContent = deg.name;
        titleSelect.appendChild(opt);
      });
    }

    // Always add custom option
    const customOpt = document.createElement('option');
    customOpt.value = '__CUSTOM__';
    customOpt.textContent = 'Other Degree (Type Manually)';
    titleSelect.appendChild(customOpt);

    // Reset subjects and input
    if (subjectsContainer) subjectsContainer.innerHTML = '';
    if (customTitleContainer) customTitleContainer.style.display = 'none';
    if (customTitleInput) {
      customTitleInput.value = '';
      customTitleInput.required = false;
    }
  }

  // Handle Degree Selection
  function updateSubjects() {
    const selectedLevel = levelSelect.value;
    const selectedTitle = titleSelect.value;

    if (selectedTitle === '__CUSTOM__') {
      if (customTitleContainer) customTitleContainer.style.display = 'block';
      if (customTitleInput) {
        customTitleInput.value = '';
        customTitleInput.required = true;
        customTitleInput.focus();
      }
      if (subjectsContainer) subjectsContainer.innerHTML = '<small class="text-muted">Enter subject manually below.</small>';
      return;
    } else {
      if (customTitleContainer) customTitleContainer.style.display = 'none';
      if (customTitleInput) {
        customTitleInput.value = selectedTitle;
        customTitleInput.required = false;
      }
    }

    const cat = SED_QUALIFICATIONS_CATALOG[selectedLevel];
    if (!cat) return;

    const degObj = cat.degrees.find(d => d.name === selectedTitle);
    if (subjectsContainer && degObj && degObj.subjects) {
      subjectsContainer.innerHTML = '';
      const selectedSubjects = new Set();

      degObj.subjects.forEach((subj, idx) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'form-check form-check-inline me-2 mb-1';

        const chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.className = 'form-check-input';
        chk.id = `${prefix}_subj_${idx}`;
        chk.value = subj;

        const lbl = document.createElement('label');
        lbl.className = 'form-check-label small';
        lbl.htmlFor = `${prefix}_subj_${idx}`;
        lbl.textContent = subj;

        chk.addEventListener('change', () => {
          if (chk.checked) {
            selectedSubjects.add(subj);
          } else {
            selectedSubjects.delete(subj);
          }
          if (subjectInput) {
            subjectInput.value = Array.from(selectedSubjects).join(', ');
          }
        });

        wrapper.appendChild(chk);
        wrapper.appendChild(lbl);
        subjectsContainer.appendChild(wrapper);
      });
    }
  }

  levelSelect.addEventListener('change', updateDegreeTitles);
  titleSelect.addEventListener('change', updateSubjects);

  // Initial trigger
  updateDegreeTitles();
}

document.addEventListener('DOMContentLoaded', () => {
  // Initialize for admin modal if present
  if (document.getElementById('admin_degree_level')) {
    initQualificationsSelector('admin');
  }
  // Initialize for teacher modal if present
  if (document.getElementById('teacher_degree_level')) {
    initQualificationsSelector('teacher');
  }
});
