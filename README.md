# PawPal+ : Project Description

This program is intended for busy pet owners.

## Model:
(UML at Mermaid.live)
  <a href="https://mermaid.live/edit#pako:eNqdVulu4zYQfhWCv5xd2_ARb7LCIkDRpE3QzQE0RdDCAMFIY4cIRaokFccJkmfvUIdFy3L3EGCZnPk494z4SmOdAI1oLLm1p4IvDU_niuBTUMhvBv7NQcVr8lqS_fPlC6g8BcOd0OrkpGFcX52x24vLs4Zy-svF17-b7d3Z2R_h_vL66va8JrzNVaj6xghthPs-zV-v7wKpZ6cXf102-_OL3887VdyKFO6ESvQqVPIx4Q4csoh13LguBqgkIDNmIDOM9Q7whOnUdL1SYG4MLMBgNMFu6RPKkZQ_s1So3IFlGRiW8HWoWMSOrAAe5ZrxJy4kvxcSYxNAluDYqvDFsoX2Ahz00H5P9-sDIoV1743L7z_mwS23j1tWI5CIpEVwwklo0RKwsRGZT1nL6SQvM1l7HrA32c-qRcBrinJRrzqzFz9AkktI2N48NpDtjN5rLYmwLNZpJsFBmxVrtZCYE7aQfNlmGmjEtvgpN48boRjsK63gx9JwA-7bWVA8bSfBZhCLrQiX5YBZfScO3yGL8SRhntjzr10zDaT6CRoEE8kOyNddIbdXV55X9RNd81Pu-uy-bBu004JZs26HBaP8TjJwIcPHBEk9_HU66-G1r_58aFFVD2XEhsPhQdFOIQKQqbHpbRW0js5txW8jdMXlHqE14gkl8SzT2HMpKNcJ5gk2IerB2ZMCzpuiMTuR35G4PyvNZnt4Yx86kGBtOLo_xlpKiOtq0T5Ne1xegvKzHzAsAidh7V95pk-CmPVJNQv3BU8bx-7XrJ4uRRnvA6NHYqmYrylmpXa2RH9LR4I9jm7Vs8L-rw54ziQXqsZsAuufAcNRlOTAdMlveepeDogfPOGBBVrGFDy7wuBePWg3JvdxhKWpcA6wc12ehUN7UGSCGa7q_g8Am0SXvTmn4zklHwaDarXTZBF54HbfidFw-AE3fqZFJOY4OAl-ukq0J3Zgi89QILTYDwYnzXUhIrmFNrf5ZITsHWs9NLgURKSuuOpAU9ceWToU4cDnSSegMrau025MqM6bRvt0aURCI2dy6FO87aTcb2nRSnPqHgDHHY1wmcCC59LN6Vy94bGMq3-0TuuTRufLBxotuLS4yzNfLdUVbwPBzx6YX3WuHI3Go0khg0av9JlGg8loePh5NBpPx5PJbHY8-3zYp2ukT4-Hn46ms-lodnT8aTydHL_16UuhdzycTWaeNJ2MDw-PZrOjPsVZ4rS5rK6Z_u_tPw2BPcU"><img width="975" height="1974" alt="image" src="https://github.com/user-attachments/assets/7d9b0c5b-e08a-4dfa-8def-6d15f1fdc74e"/></a>
### How it works:
- Owner owns OwnerPreferences and a list of Pets
  - Owner can set Preferences for windows of free time so autoscheduler will know where to move tasks with unspecified times 
- Pet owns a list of Tasks
  - User / owner creates tasks through pets, so they are linked to individual pets
- Scheduler is stateless and operates on Owner/Task/TimeWindow objects
- Task references both Priority and Frequency enums

## Usage:
When run, the app will:  
- Let a user enter basic owner + pet info (owner name, pet name)
- Allow profile switching
- Let a user add/edit tasks (with duration and/or time range as well as priority ranking)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly with basic reasoning for selected time
- Warn user if overscheduling a time slot
- Request updated time if a conflict arises in same-priority or scheduled time slot 


## Setup & Run 

```bash
pip install -r requirements.txt
streamlit run app.py
```
