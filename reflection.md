# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?
- > Owner: Name, pets owned (links to pet), tasks completed / tasks,
  > Tasks: Date, str task name, str description, and bool completed
  >   > monthly/weekly grooming/vet checkup
  >   > daily food, water
  >   > other maintence may be SPECIES-specific (cat) so, is using AI later, maybe have draw fom I for a known animal group's anima
  > Pet: name, owner (links to owner), >> attaches persistent tasks daily/monthly/yearly
 ^ with Claude
 v with copilot not in-line, fleshed out using Claude
Main/Original prompt classes
> Owner: id, Name, pets owned, timezone. 
    > can add_pet, get_pets(), schedule_task( saved on pet ), see_todays_tasks(date), 
> Pet: id, name, species, tasks
    > can add_task, get_task, remove_task
> Scheduler: collect, generate, sort tasks and arrange by priority, assign time slots, explain
> Tasks: details on the pet, title, description, duration, start and endtime, frequency, and completion. can mark completion   
and classes to fit needs of schedule/task coordination
> Frequency: enumeration for how often the event happens
> TimeWindow : start time, end time --> how many minutes/hours will it take
 
  
**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

From UML to stubs 
> changed task creation from a method under pet to a method in Owner that stores in Pet, so the owner can schedule tasks.
> originally planned to make household-based, so many-to-many owner to pet, but decided 1 owner to many pets should work first
Class stubs to classes 
> changed how time logic because it was inconsistent and could allow errors when changing time zone.
After first implementation
> kept making gradual changes as I noticed bugs, and some became design changes, like time availability options and priority ranking.
  
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?
> My scheduler has options for set time range/start time for the event or just duration. 
> When deciding scheduling time, it defaults to scheduled > unscheduled the high > low priority when deciding what goes where
> Finally, I added user availability options to make the default times remain within that range

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
> If there is a high priority event, the program (should) shift the time for a low priority event or any unscheduled events (still but notify the user there is a conflict and allow them to change it) 

- Why is that tradeoff reasonable for this scenario?
> For example, if your dog has to go to a vet appointment (high priority) and they're only open at a specific time slot, that should override taking him on a walk (low priority) even if it's scheduled at the same time, since you can still walk him later. (high scheduled > low scheduled: bumps walk scheduled time to after the appointment)
> If the vet is open all day, then walk him at the same time since you can get there anyways (low scheduled > high unscheduled > low unscheduled: keep your walk appointment but going to the vet takes priority over other tasks).
> Ideally my program still follows that logic

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
> I fed it my ideas for the design, asked how realistic it would be, then used it to update the logic. 
> I checked the logic and asked it do turn it into stubs, then to develop those stubs the way I wanted.

> I didn't use it for debugging as much as I should've, as I'm not as used to using pytest, but it did test a few things on its own.

- What kinds of prompts or questions were most helpful?
> simple questions like why (why did you want to change this/not change this), how does this fit the model, and describe what this class does: 
> usually I left detailed descriptions of how I wanted the program to work and that seemed to work well 

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
> Most of the project.
> First, I had it rework the logic for the UML. I asked Claude and after a certain point of fleshing it out, it seemed wrong so I asked Copilot a reworked question, asked it to compare to Claude's model for my goals, and had it combine the working parts of both.

- How did you evaluate or verify what the AI suggested?
> I read through it and the summary of why it did something. I kept "Ask before edits" and/or "Plan mode" on at all times and checked the "Thinking ^" dropdown to see if it was understanding my reasoning

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?
> 1. Does it save user input? for pet, user name, tasks? 
At minimum, I need it to remember the user, link the pet to them, and to save the tasks to a pet. 
I manually tested changing user name and there was no way to return, so I changed it to a pseudo account system. 
> 2. How does it handle event conflicts
I tested setting 2 events at the same time with different priorities. First implementation, it just warned the user of a conflict, but I reworked with Claude so it would shift lower priorities and offer user to change. 
After, I tested with scheduling the same block with different pets with different priority levels and it moved the lower priority one.
> 3. How does it handle user availability?
I tested setting a recurring event to 8 to 9 AM daily but setting user availability at 6AM to 9AM on some days, and it rescheduled the event on those days to 6 to 7 AM.


**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?
> I'm fairly confident it works well, though I know it could be implemented better with more time
> I would test fitting into different specific schedules day-to-day, test how it handles scheduling when under the duration minimum, and test for multiple users with multiple pets. 

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
> I think the rescheduling section worked pretty well. Otherwise, I think saving progress across multiple accounts worked surprisingly well, though I don't know if it'd scale well.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
>I would redo the avalibiliry range selection because it's a bit too big. If I had more time, I'd like to a system for shared pets and keeping track of shared duties would work, as well as some checklist feature so shared duties could be marked off by either party to let the other person know it's already done. I would also update the explaination to remove the long timestamp and maybe generate a reason for the priority ranking or at least say "no description" when none is given by the user.
> Overall, if I worked on it again, I'd come at it more organized and save myself way more time, since I ended up getting caught up on the early steps, fleshing it out naturally, and missing that there were more detailed instructions for the later steps by the time the deadline hit.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
> You have to be very specific about what you want (and have a clear plan of how to ask it ahead of time) because, if you aren't from the start, it will keep trying to undo your suggestions at every step.