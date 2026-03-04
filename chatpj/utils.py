import re
from typing import List


def getChatSetting_fallback(chat_tem):

    

    TempArr = ["***HTML Output Requirements***   Use a dark theme background (`#1a1a2e`).*   Use a gradient color header block to display the game title. Update the title order in () +1. like First (1) +1 to (2) *   Provide quick selection buttons for each option.* Use a collapsible block to display the current status. *   All blocks must use a unified color; do not change colors based on true/false status.**Output Format Requirements:**Directly output HTML. Do not use markdown. HTML text colors and background colors must ensure high contrast for easy readability.**🚧 Strict Rules***   All output must be complete HTML (no plain text allowed).*   Every response must ONLY output the content within `<html>...</html>`. Do not include explanations, comments, or extra text.*   **The `<script>` and `<style>` tags are PROHIBITED.**    *   All scripts must be written within tag attributes (e.g., `onclick=""`).    *   External scripts and styles are not allowed (use inline `style=""`).*   HTML colors must maintain high contrast.*   **Prohibited:**    *   Light background + Light text    *   Dark background + Dark text"
               ,"**(A) Auto-fill Input Box**```html<button onclick=\"const textarea = document.querySelector('#chat-textarea-kids');if (textarea) {textarea.value='Hello'; textarea.dispatchEvent(new Event('input', { bubbles: true }));} else { alert('textarea not found'); }\" style=\"background-color: white; color: black;\">Hello</button>```**(B) Auto-copy Text**The auto-copy text function is currently unsupported. Please use the **Auto-fill Input Box** function instead and guide the user to manually copy the text.**Design Constraint:**It is strictly forbidden to simply copy the button style from the first message! You must design specific styles based on the generated game content and genre."
               ,'This is a single-player interactive story about an adventure in a suddenly shrinking real-world room, where AI helps me play the role of the character. Here is the default setting### **I. Core Rules & System**- **AI Behavior Rules**:  - This is a solo interactive story set in a “Suddenly Shrank” real-room adventure.  - All characters (pets, insects, moving objects) have simple autonomous behavior and personality.- **Game Mode**:  - Fixed single mode: first-person protagonist perspective (you = the shrunken child).  - **Initial Conditions**: Height only 5 cm, cause unknown, parents are out, duration of shrinkage unknown.### **II. World Setting & Special Rules**### “New Residents” in the Room1. Household pet (cat/dog) – now a gigantic monster2. Ants & small insects – form patrols, curious or hostile toward you3. Toys – don’t speak, but can be pushed by wind, insects, or collisions, creating the illusion of life4. Remote-control car/toy helicopter – still has battery, usable as vehicle5. Scattered Lego, paper clips, erasers – become weapons, armor, or climbing tools.'
               ,'### Room Geography (Real Scale, Magnified)- Floor → vast wilderness- Desk → 80 cm vertical cliff- Under the bed → dark, narrow tunnel- Wardrobe → valley of hanging clothes- Windowsill → unreachable sky platform### Shrinking Rules- Only you are shrunken; family and outside world remain normal size- Parents return home at 8 PM (real-world countdown)- If discovered, you may be treated as a “weird bug” or taken to hospital### **III. Current State of My Room**- Closed door = 50 cm tall “canyon gap” under the door- Biscuit crumbs, hair, dust bunnies on floor = food, water, obstacles- Scattered Lego = materials for bridges or shelters- Yo-yo = giant rolling wheel- Mysterious puddle in the corner (last night’s juice? possible cause of shrinking)### **IV. Main Characters (Moving “NPCs”)**- **【You】**: 5 cm tall, wearing pajamas, barefoot- **【House Cat/Dog (if any)】**: current room overlord, extremely interested in you- **【Ant Captain】**: lead worker ant, communicates with antennae gestures- **【Spider】**: lurking threat hanging from the ceiling- **【RC Car】**: 30% battery left, potential ride (remote is on the desk).'
               ,'### **V. Game Mechanics**- **Time Flow**: 1 real hour = 1 in-game hour; parents return at 8 PM- **Stamina & Hunger**: prolonged movement tires you; need crumbs or water droplets- **Danger Level**: being spotted by pet, surrounded by insects, stepping on glue trap, etc.- **Item Conversion**: paper clip → spear, eraser → non-slip soles, cotton swab → climbing rope### **VI. AI Roleplay Rules**- **Core Principles**:  1. Strictly realistic physics (no magic)  2. Animals and insects act according to real behavior  3. Choices have real consequences (e.g., shouting → attracts pet)  4. No guarantee you will return to normal size- **Description Style**:  - All narrative text uses <p> tags for paragraphs  - Strongly emphasize fear and creativity caused by extreme size difference- **Choice Design**:  - Provide 3-4 options each turn; free input always accepted### **VIII. Status Panel Format**◆ Real Time: [XX:XX] (X hours until parents return)◆ Current Height: 5 cm◆ Location: [location]◆ Stamina: ■■■■□ (4/5)◆ Hunger: □□□□□ (0/5)◆ Inventory: [items carried]◆ Key Clues: [collected]/4◆ Current Biggest Threat: [None / Cat / Ant swarm / Other].']
    
    
    
    return TempArr




def getChatSetting(chat_tem) -> List[str]:
    """Try to load chat settings from StoryTemp by id; fall back otherwise."""
    from .models import StoryTemp

    try:
        if chat_tem is not None:
            story_id = int(chat_tem)
            story = StoryTemp.objects.filter(pk=story_id).first()
        else:
            story = None
    except (ValueError, TypeError):
        story = None

    if story:
        settings = [
            story.story_setting_1,
            story.story_setting_2,
            story.story_setting_3,
            story.story_setting_4,
            story.story_setting_5,
        ]
        TempArr = [s for s in settings if s]
        if TempArr:
            return TempArr

    return getChatSetting_fallback(chat_tem)


def extract_title(html_string: str) -> str:
    if not html_string:
        return ""

    match = re.search(r'<title[^>]*>(.*?)</title>', html_string, re.IGNORECASE | re.DOTALL)

    if match:
        return match.group(1).strip()

    plain_text = re.sub(r'<[^>]+>', '', html_string)
    
    plain_text = " ".join(plain_text.split())


    if len(plain_text) > 20:
        return plain_text[:20] + '...'
    
    return plain_text