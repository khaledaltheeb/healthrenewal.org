from __future__ import annotations


def s(publisher: str, title: str, url: str, year: int) -> dict:
    return {"publisher": publisher, "title": title, "url": url, "year": year}


SOURCES = {
    "suicide": [
        s("World Health Organization", "Suicide fact sheet", "https://www.who.int/news-room/fact-sheets/detail/suicide", 2025),
        s("World Health Organization", "LIVE LIFE: an implementation guide for suicide prevention", "https://www.who.int/publications/i/item/9789240026629", 2021),
        s("NICE", "Self-harm: assessment, management and preventing recurrence", "https://www.nice.org.uk/guidance/ng225/chapter/Recommendations", 2022),
    ],
    "panic": [
        s("NICE", "Generalised anxiety disorder and panic disorder in adults", "https://www.nice.org.uk/guidance/cg113/chapter/Recommendations", 2026),
        s("NHS", "Panic disorder", "https://www.nhs.uk/mental-health/conditions/panic-disorder/", 2026),
        s("World Health Organization", "Doing What Matters in Times of Stress", "https://www.who.int/publications/i/item/9789240003927", 2020),
    ],
    "trauma": [
        s("World Health Organization", "Psychological first aid: Guide for field workers", "https://www.who.int/publications/i/item/9789241548205", 2011),
        s("NICE", "Post-traumatic stress disorder", "https://www.nice.org.uk/guidance/ng116/chapter/Recommendations", 2018),
        s("National Center for PTSD", "Understanding PTSD and trauma", "https://www.ptsd.va.gov/understand/index.asp", 2026),
    ],
    "crisis": [
        s("World Health Organization", "Psychological first aid", "https://www.who.int/publications/i/item/9789241548205", 2011),
        s("NICE", "Violence and aggression: short-term management", "https://www.nice.org.uk/guidance/ng10/chapter/Recommendations", 2015),
        s("NHS", "Urgent help for mental health", "https://www.nhs.uk/nhs-services/mental-health-services/where-to-get-urgent-help-for-mental-health/", 2026),
    ],
    "services": [
        s("NICE", "Shared decision making", "https://www.nice.org.uk/guidance/ng197/chapter/Recommendations", 2021),
        s("World Health Organization", "Guidance on community mental health services", "https://www.who.int/publications/i/item/9789240025707", 2021),
        s("NHS", "Mental health services", "https://www.nhs.uk/nhs-services/mental-health-services/", 2026),
    ],
    "violence": [
        s("World Health Organization", "Violence against women", "https://www.who.int/news-room/fact-sheets/detail/violence-against-women", 2024),
        s("World Health Organization", "Responding to intimate partner violence and sexual violence", "https://www.who.int/publications/i/item/9789241548595", 2013),
        s("World Health Organization", "Violence against children", "https://www.who.int/news-room/fact-sheets/detail/violence-against-children", 2024),
    ],
    "youth": [
        s("World Health Organization", "Adolescent mental health", "https://www.who.int/news-room/fact-sheets/detail/adolescent-mental-health", 2025),
        s("UNICEF", "Mental health and well-being", "https://www.unicef.org/parenting/mental-health", 2026),
        s("CDC", "Children's mental health", "https://www.cdc.gov/children-mental-health/about/index.html", 2026),
    ],
    "wandering": [
        s("NICE", "Dementia: assessment, management and support", "https://www.nice.org.uk/guidance/ng97/chapter/Recommendations", 2025),
        s("National Institute on Aging", "Wandering and Alzheimer's disease", "https://www.nia.nih.gov/health/safety/wandering-and-alzheimers-disease", 2026),
        s("World Health Organization", "Disability and health", "https://www.who.int/news-room/fact-sheets/detail/disability-and-health", 2023),
    ],
    "anxiety": [
        s("NICE", "Generalised anxiety disorder and panic disorder in adults", "https://www.nice.org.uk/guidance/cg113/chapter/Recommendations", 2026),
        s("NICE", "Social anxiety disorder", "https://www.nice.org.uk/guidance/cg159/chapter/Recommendations", 2024),
        s("NHS", "Anxiety, fear and panic", "https://www.nhs.uk/mental-health/feelings-symptoms-behaviours/feelings-and-symptoms/anxiety-fear-panic/", 2026),
    ],
    "perinatal": [
        s("NICE", "Antenatal and postnatal mental health", "https://www.nice.org.uk/guidance/cg192/chapter/Recommendations", 2025),
        s("World Health Organization", "Maternal mental health", "https://www.who.int/teams/mental-health-and-substance-use/promotion-prevention/maternal-mental-health", 2026),
        s("NHS", "Postnatal depression", "https://www.nhs.uk/mental-health/conditions/post-natal-depression/overview/", 2026),
    ],
    "mood": [
        s("NICE", "Depression in adults: treatment and management", "https://www.nice.org.uk/guidance/ng222/chapter/Recommendations", 2022),
        s("World Health Organization", "Depressive disorder", "https://www.who.int/news-room/fact-sheets/detail/depression", 2025),
        s("NHS", "Clinical depression", "https://www.nhs.uk/mental-health/conditions/clinical-depression/overview/", 2026),
    ],
    "bipolar": [
        s("NICE", "Bipolar disorder: assessment and management", "https://www.nice.org.uk/guidance/cg185/chapter/Recommendations", 2025),
        s("NHS", "Bipolar disorder", "https://www.nhs.uk/mental-health/conditions/bipolar-disorder/", 2026),
        s("National Institute of Mental Health", "Bipolar disorder", "https://www.nimh.nih.gov/health/topics/bipolar-disorder", 2026),
    ],
    "developmental": [
        s("NICE", "Learning disabilities and behaviour that challenges", "https://www.nice.org.uk/guidance/ng11/chapter/Recommendations", 2015),
        s("NICE", "Service design and delivery for people with a learning disability", "https://www.nice.org.uk/guidance/ng93/chapter/Recommendations", 2018),
        s("World Health Organization", "Disability and health", "https://www.who.int/news-room/fact-sheets/detail/disability-and-health", 2023),
    ],
    "learning": [
        s("CDC", "Learning disorders in children", "https://www.cdc.gov/children-mental-health/about/about-learning-disorders.html", 2026),
        s("UNICEF", "Inclusive education", "https://www.unicef.org/education/inclusive-education", 2026),
        s("World Health Organization", "Disability and health", "https://www.who.int/news-room/fact-sheets/detail/disability-and-health", 2023),
    ],
    "communication": [
        s("National Institute on Deafness and Other Communication Disorders", "Speech and language", "https://www.nidcd.nih.gov/health/speech-and-language", 2026),
        s("CDC", "Developmental monitoring and screening", "https://www.cdc.gov/ncbddd/actearly/index.html", 2026),
        s("World Health Organization", "Disability and health", "https://www.who.int/news-room/fact-sheets/detail/disability-and-health", 2023),
    ],
    "access": [
        s("World Health Organization", "Disability and health", "https://www.who.int/news-room/fact-sheets/detail/disability-and-health", 2023),
        s("World Health Organization", "Global report on health equity for persons with disabilities", "https://www.who.int/publications/i/item/9789240063600", 2022),
        s("NICE", "Patient experience in adult NHS services", "https://www.nice.org.uk/guidance/cg138/chapter/Recommendations", 2021),
    ],
    "safeguarding": [
        s("World Health Organization", "Comprehensive sexuality education", "https://www.who.int/news-room/questions-and-answers/item/comprehensive-sexuality-education", 2023),
        s("UNICEF", "Child protection", "https://www.unicef.org/protection", 2026),
        s("World Health Organization", "Violence against children", "https://www.who.int/news-room/fact-sheets/detail/violence-against-children", 2024),
    ],
    "rights": [
        s("NICE", "Decision-making and mental capacity", "https://www.nice.org.uk/guidance/ng108/chapter/Recommendations", 2018),
        s("NICE", "Shared decision making", "https://www.nice.org.uk/guidance/ng197/chapter/Recommendations", 2021),
        s("World Health Organization", "Guidance on community mental health services", "https://www.who.int/publications/i/item/9789240025707", 2021),
    ],
    "medication": [
        s("NICE", "Medicines optimisation", "https://www.nice.org.uk/guidance/ng5/chapter/Recommendations", 2015),
        s("NICE", "Shared decision making", "https://www.nice.org.uk/guidance/ng197/chapter/Recommendations", 2021),
        s("NHS", "Medicines information", "https://www.nhs.uk/medicines/", 2026),
    ],
    "dementia": [
        s("NICE", "Dementia: assessment, management and support", "https://www.nice.org.uk/guidance/ng97/chapter/Recommendations", 2025),
        s("National Institute on Aging", "Alzheimer's and related dementias", "https://www.nia.nih.gov/health/alzheimers-and-dementia", 2026),
        s("World Health Organization", "Dementia fact sheet", "https://www.who.int/news-room/fact-sheets/detail/dementia", 2025),
    ],
    "delirium": [
        s("NICE", "Delirium: prevention, diagnosis and management", "https://www.nice.org.uk/guidance/cg103/chapter/Recommendations", 2023),
        s("NHS", "Sudden confusion (delirium)", "https://www.nhs.uk/conditions/confusion/", 2026),
        s("National Institute on Aging", "Older adults and hospitalization", "https://www.nia.nih.gov/health/what-do-after-someone-hospitalized", 2026),
    ],
    "older": [
        s("World Health Organization", "Mental health of older adults", "https://www.who.int/news-room/fact-sheets/detail/mental-health-of-older-adults", 2023),
        s("NICE", "Depression in adults", "https://www.nice.org.uk/guidance/ng222/chapter/Recommendations", 2022),
        s("National Institute on Aging", "Mental and emotional health", "https://www.nia.nih.gov/health/mental-and-emotional-health", 2026),
    ],
    "substance": [
        s("World Health Organization", "Alcohol fact sheet", "https://www.who.int/news-room/fact-sheets/detail/alcohol", 2024),
        s("SAMHSA", "Substance use disorder treatment and family therapy", "https://store.samhsa.gov/product/tip-39-substance-use-disorder-treatment-and-family-therapy/PEP20-02-02-012", 2020),
        s("World Health Organization", "Mental health and substance use", "https://www.who.int/teams/mental-health-and-substance-use", 2026),
    ],
    "alcohol": [
        s("World Health Organization", "Alcohol fact sheet", "https://www.who.int/news-room/fact-sheets/detail/alcohol", 2024),
        s("NICE", "Alcohol-use disorders: diagnosis and management", "https://www.nice.org.uk/guidance/cg115/chapter/Recommendations", 2011),
        s("NHS", "Alcohol support", "https://www.nhs.uk/live-well/alcohol-advice/alcohol-support/", 2026),
    ],
    "opioid": [
        s("World Health Organization", "Opioid overdose", "https://www.who.int/news-room/fact-sheets/detail/opioid-overdose", 2025),
        s("World Health Organization", "Community management of opioid overdose", "https://www.who.int/publications/i/item/9789241548816", 2014),
        s("SAMHSA", "Overdose prevention and response toolkit", "https://store.samhsa.gov/product/overdose-prevention-and-response-toolkit/pep23-03-00-001", 2023),
    ],
    "gambling": [
        s("World Health Organization", "Gambling fact sheet", "https://www.who.int/news-room/fact-sheets/detail/gambling", 2024),
        s("NICE", "Gambling-related harms", "https://www.nice.org.uk/guidance/ng248/chapter/Recommendations", 2025),
        s("NHS", "Help for problems with gambling", "https://www.nhs.uk/live-well/addiction-support/gambling-addiction/", 2026),
    ],
    "gaming": [
        s("World Health Organization", "Gaming disorder", "https://www.who.int/news-room/questions-and-answers/item/addictive-behaviours-gaming-disorder", 2020),
        s("World Health Organization", "ICD-11 gaming disorder", "https://www.who.int/standards/classifications/frequently-asked-questions/gaming-disorder", 2026),
        s("UNICEF", "Healthy screen time", "https://www.unicef.org/parenting/child-care/healthy-screen-time", 2026),
    ],
    "nicotine": [
        s("World Health Organization", "Tobacco fact sheet", "https://www.who.int/news-room/fact-sheets/detail/tobacco", 2025),
        s("CDC", "How to quit smoking", "https://www.cdc.gov/tobacco/campaign/tips/quit-smoking/index.html", 2026),
        s("NHS", "Quit smoking", "https://www.nhs.uk/better-health/quit-smoking/", 2026),
    ],
    "sleep": [
        s("NHS", "Insomnia", "https://www.nhs.uk/conditions/insomnia/", 2026),
        s("NICE", "Insomnia", "https://cks.nice.org.uk/topics/insomnia/", 2026),
        s("National Heart, Lung, and Blood Institute", "Healthy sleep habits", "https://www.nhlbi.nih.gov/health/sleep-deprivation/healthy-sleep-habits", 2026),
    ],
    "pain": [
        s("NICE", "Chronic pain in over 16s", "https://www.nice.org.uk/guidance/ng193/chapter/Recommendations", 2021),
        s("World Health Organization", "Guidelines on chronic pain management", "https://www.who.int/publications/i/item/9789240017870", 2020),
        s("NHS", "Living with chronic pain", "https://www.nhs.uk/live-well/pain/how-to-get-nhs-help-for-your-pain/", 2026),
    ],
    "chronic": [
        s("World Health Organization", "Integrated people-centred care", "https://www.who.int/health-topics/integrated-people-centered-care", 2026),
        s("NICE", "Multimorbidity: clinical assessment and management", "https://www.nice.org.uk/guidance/ng56/chapter/Recommendations", 2016),
        s("NHS", "Caring for someone with a long-term condition", "https://www.nhs.uk/conditions/social-care-and-support-guide/practical-tips-if-you-care-for-someone/caring-for-someone-with-a-long-term-condition/", 2026),
    ],
    "work": [
        s("World Health Organization", "Mental health at work", "https://www.who.int/news-room/fact-sheets/detail/mental-health-at-work", 2024),
        s("World Health Organization", "Guidelines on mental health at work", "https://www.who.int/publications/i/item/9789240053052", 2022),
        s("NICE", "Workplace health: long-term sickness absence", "https://www.nice.org.uk/guidance/ng146/chapter/Recommendations", 2019),
    ],
}

SOURCES["learning_disability"] = SOURCES["developmental"]
SOURCES["sensory"] = SOURCES["developmental"]
