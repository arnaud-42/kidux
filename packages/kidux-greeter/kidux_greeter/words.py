"""What only the trusted screens say: sign-in, lock, first-run wizard, panel.

Words more than one program shows live in `kidux.vocabulary`; these are the
sentences no other screen has a reason to use. Marked here, translated where
they are shown, in whichever language the screen is in at that moment.
"""

from kidux.i18n import N_

# --- the sign-in and lock screens ---------------------------------------------

WHO_IS_USING = N_("Who is using the computer?")
NOBODY_YET = N_("There is nobody here yet. An adult can add children.")
LOCKED = N_("The computer is locked.")
WHAT_NOW = N_("What would you like to do?")
SOMETHING_WENT_WRONG = N_("Something went wrong. Try again, or turn the computer off.")
ADULT_PANEL = N_("Adult panel")

# --- the first-run wizard -----------------------------------------------------

WELCOME = N_("Welcome to Kidux")
WHICH_KEYBOARD = N_("Which keyboard does this computer have?")
CHOOSE_ADULT_PASSWORD = N_("Choose the adult password")
ADULT_PASSWORD_EXPLAINED = N_(
    "It opens the adult panel, where you decide what each child may use. "
    "Choose one the children will not guess, and do not let them see you type it."
)
LONGER_IS_SAFER = N_("A longer password is harder to guess.")
SHARE_STATISTICS_HEADING = N_("Help count Kidux's computers?")
SHARE_STATISTICS_EXPLAINED = N_(
    "When this computer looks for updates, it tells Kidux's server that it is a Kidux "
    "computer. With this on, it adds an identifier made for this computer alone, so that "
    "it is counted as one computer and not as an address. Nothing else is sent: no name, "
    "no version, nothing of a child's. It can be changed later on the System page, under "
    "Advanced."
)
SHARE_STATISTICS = N_("Share usage statistics")
SHARE_STATISTICS_HINT = N_(
    "An identifier made for this computer alone goes with each look for updates, so that "
    "Kidux's server counts it as one computer. Nothing else: no name, no version, nothing "
    "of a child's."
)
TYPE_IT_AGAIN = N_("Type it again")
PASSWORDS_DIFFER = N_("The two passwords are not the same. Try again.")
PASSWORD_NEEDED = N_("The password cannot be empty.")
UNLOCK_TO_FINISH = N_("Type the adult password to finish setting up the computer.")
ALL_SET = N_("Everything is ready.")
ALL_SET_EXPLAINED = N_("You can add more children and change anything later from the adult panel.")

# --- a child's form, in the wizard and in the panel ---------------------------

FIRST_CHILD = N_("Add the first child")
NAME_NEEDED = N_("Write the child's name.")
CHILD_PASSWORD_EXPLAINED = N_("The child types it to sign in. For a young child it can be very simple.")
HOW_MAY_THEY_USE = N_("How may they use the computer?")
MINUTES_A_DAY = N_("Minutes a day")
#: The days of the week a child's time is for (D54), Monday first, each
#: short enough for seven boxes on one row.
DAYS = N_("Days")
WEEKDAYS = (N_("Mon"), N_("Tue"), N_("Wed"), N_("Thu"), N_("Fri"), N_("Sat"), N_("Sun"))
SAVE = N_("Save")
ADD = N_("Add")
NOT_SAVED = N_("This was not saved. Check it and try again.")
SOME_NOT_SAVED = N_("Some changes were not saved. Look at the fields marked below.")

# --- keyboards, by the name an adult knows them by ----------------------------

KEYBOARD_ES = N_("Spanish (Spain)")
KEYBOARD_LATAM = N_("Latin American")
KEYBOARD_US = N_("English (US)")
KEYBOARD_GB = N_("English (UK)")

# --- the adult panel ----------------------------------------------------------

CHILDREN = N_("Children")
MODULES = N_("Modules")
SYSTEM = N_("System")
CLOSE = N_("Close")
ADD_CHILD = N_("Add a child")
NAME = N_("Name")
PICTURE = N_("Picture")
LANGUAGE = N_("Language")
PASSWORD = N_("Password")
USED_TODAY = N_("Used today")
REMOVE = N_("Remove")
REMOVE_QUESTION = N_("Remove this child?")
REMOVE_EXPLAINED = N_("Their account and everything in it will be deleted from this computer.")
REMOVE_KEEP_FILES = N_("Remove, but keep their files")
CANNOT_REMOVE_SIGNED_IN = N_("This child is signed in. They have to log out first.")
SAVED = N_("Saved.")
#: The display scale that suits the screen, which a machine has until an
#: adult chooses one (D49).
AUTOMATIC = N_("Automatic ({size})")
#: What marks a size that is not a whole multiple of 100 %, and why (D59):
#: an X11 program is drawn at 1 and enlarged, soft at such a size.
NOT_PREFERRED_MARK = N_("*")
SCALE_NOTE = N_(
    "Sizes with * can make a module that uses XWayland look blurred; if one does, "
    "choose a size without *.")
#: A child's setting that opens their modules in windows (D46), what it
#: does, and what a module that needs it says on the Modules page.
WINDOWS = N_("Windows")
WINDOWS_EXPLAINED = N_(
    "Modules in windows they move, resize and put full screen, several at once; "
    "from their next sign-in.")
NEEDS_WINDOWS = N_("Needs windows")
#: After the description of a module no package installed, a folder copied
#: under the modules directory by hand, as the tests' stand-ins are (D101).
NOT_FROM_A_PACKAGE = N_("A folder, not from a package")
#: Who a module is for (D55), under its description on the Modules page:
#: its ages, with one bound or both, and the modules best done before it.
AGES_FROM_TO = N_("Ages {least} to {most}")
AGES_FROM = N_("Ages {least} and up")
AGES_TO = N_("Ages up to {most}")
FIRST = N_("Recommended before: {modules}")
#: The System page's way to the settings that depend on the machine's
#: hardware (D52), and that page.
ADVANCED = N_("Advanced")
ADVANCED_OPEN = N_("Pointer, touchpad and Chromium")
ADVANCED_EXPLAINED = N_("How this computer's pointer moves, and what to try if something "
                        "does not work on it.")
#: The pointer's speed and the touchpad's scroll (kidux.pointer), each in
#: five steps, slower to faster, the middle one Kidux's own.
POINTER_SPEED = N_("Pointer speed")
TWO_FINGER_SCROLL = N_("Scrolling with two fingers")
SPEED_STEPS = (N_("Much slower"), N_("Slower"), N_("Normal"), N_("Faster"), N_("Much faster"))
POINTER_EXPLAINED = N_("On a touchpad, two fingers scroll the page; Normal scrolls half "
                       "as far as most computers do.")
APPLIES_NEXT_SIGN_IN = N_("Saved. It applies the next time a child signs in.")
#: The panel's Suspend and hibernate page (D119), in an adult's words:
#: suspend keeps the computer's memory powered, hibernate saves it to the
#: disk and turns the computer off.
POWER_OPEN = N_("Suspend and hibernate")
POWER = N_("Suspend and hibernate")
LID_CLOSES = N_("When the lid closes")
LID_HINT = N_("With another screen connected, closing the lid only turns this screen off.")
IDLE_ACTION = N_("Action when idle")
IDLE_HINT = N_("The screen can turn off earlier: that is set on the System page.")
AFTER = N_("after")
POWER_SLEEP_THEN_HIBERNATE = N_("Suspend, then hibernate after a minute")
POWER_SLEEP = N_("Suspend")
POWER_NOTHING = N_("Nothing")
POWER_SCREEN_OFF_ONLY = N_("Only turn the screen off")
SUSPEND_EXPLAINED = N_("Suspend: little battery use, and the computer comes back at once.")
HIBERNATE_EXPLAINED = N_("Hibernate: no battery use. It needs a swap space on the disk.")
#: Where the guide, in the screen's language, says how to make a swap space.
SWAP_GUIDE_URL = N_("https://github.com/othermore/kidux/blob/main/docs/en/user-guide.md"
                    "#making-a-swap-space")
NO_HIBERNATE_NO_SWAP = N_("Warning: this computer has no swap space, so hibernating will not "
                          "work. If you choose to hibernate, the computer suspends instead. "
                          "The guide says how to make a swap space: {url}")
NO_HIBERNATE_SECURE_BOOT = N_("Warning: Secure Boot is on in this computer, and then Linux does "
                              "not let it hibernate. If you choose to hibernate, the computer "
                              "suspends instead.")
NO_HIBERNATE = N_("Warning: hibernating does not work on this computer, often because its swap "
                  "space is smaller than its memory. If you choose to hibernate, the computer "
                  "suspends instead. The guide says how to make a swap space: {url}")
CANNOT_SLEEP = N_("Warning: this computer can neither suspend nor hibernate. Whatever you "
                  "choose, closing the lid or leaving it idle only locks it and turns the "
                  "screen off.")
CHROMIUM_OPTIONS = N_("Chromium's options")
CHROMIUM_OPTIONS_EXPLAINED = N_(
    "If a web module, Scratch for instance, or ScratchJr, which is Chromium inside, "
    "is drawn wrong on this computer, with noise or old pictures in it, try these, one "
    "at a time and in this order, saving each and opening the module again. One option "
    "a line; empty is what Kidux does on its own.")
#: The options worth trying, in the order of rollout.md section 5, each with
#: what it does. The options themselves are Chromium's, never translated;
#: the third is two lines that go together.
CHROMIUM_OPTION_LIST = (
    ("--disable-gpu-compositing",
     N_("Chromium puts the page together itself. The likeliest cure.")),
    ("--disable-gpu", N_("Nothing on the graphics card. Slower.")),
    ("--use-gl=angle\n--use-angle=gl", N_("Another way of drawing: the two lines together.")),
    ("--disable-features=WaylandLinuxDrmSyncobj",
     N_("The newer way of handing pictures to the screen, turned off.")),
)
OPTION_NOT_ACCEPTED = N_(
    "An option was not accepted. Each starts with --, has no spaces, and does not "
    "change which page or profile Chromium opens.")
TIME_GIVEN = N_("Time given.")
#: The number an adult sets a child's time left today to, and its button.
LEFT_TODAY = N_("Left today")
SET = N_("Set")
TIME_SET = N_("Time left set.")
NO_LIMIT_TO_SET = N_("This child has no time limit.")
CHILD_ADDED = N_("Child added.")
CHILD_REMOVED = N_("Child removed.")
NO_MODULES_YET = N_("No learning modules are installed on this computer yet.")
ADD_MODULES = N_("Add modules")
#: How the Modules page's lists are ordered (D73), said above them.
MODULES_BY_AGE = N_("From the youngest to the oldest; the test modules, [Test], last.")
#: The box that narrows both lists to the modules whose name or description
#: has what is typed.
FIND_A_MODULE = N_("Find a module")
LOOK_FOR_MODULES = N_("Look for modules")
LOOKING_FOR_MODULES = N_("Looking for modules…")
ALL_MODULES_INSTALLED = N_("Every module the archive offers is installed.")
NO_MODULE_SOURCE = N_("This computer has no source of modules.")
REMOVE_MODULE_QUESTION = N_("Remove {name}? The children's own files stay.")
REMOVE_FOLDER_QUESTION = N_("Remove the folder of {name}? The children's own files stay.")
MODULES_WAIT = N_("Children are signed in. Modules can be installed and removed once they "
                  "have logged out.")
INSTALLING_MODULE = N_("Installing…")
#: A module's own settings for each child (D90): the button in its row, and
#: the page it opens.
MODULE_SETTINGS = N_("Settings")
MODULE_SETTINGS_TITLE = N_("{name}: settings")
MODULE_SETTINGS_HOW = N_("Each child has their own. A change is saved as soon as it is made.")
SECRET_IS_SET = N_("Set. Type a new one to change it.")
SECRET_FORGET = N_("Forget")
REMOVING_MODULE = N_("Removing…")
#: A module's row while its install or removal waits for the one before.
WAITING = N_("Waiting…")
MODULE_INSTALLED = N_("Installed.")
MODULE_REMOVED = N_("Removed.")
MODULE_FAILED = N_("That did not work.")
VERSION = N_("Version")
LOOK_FOR_UPDATES = N_("Look for updates")
LOOKING_FOR_UPDATES = N_("Looking for updates…")
UP_TO_DATE = N_("Everything is up to date.")
INSTALL = N_("Install")
INSTALLING = N_("Installing updates…")
UPDATED = N_("The updates are installed.")
RESTART_TO_FINISH = N_("Restart the computer to finish.")
RESTART_NOW = N_("Restart now")
UPDATE_FAILED = N_("Something went wrong with the updates.")
UPDATES_WAIT = N_("Children are signed in. Updates can be installed once they have logged out.")
UPDATE_BUSY = N_("An update is already running.")
KEYBOARD = N_("Keyboard")
RECOVERY_PASSWORD = N_("Recovery password")
RECOVERY_EXPLAINED = N_(
    "It starts the computer another way, from the boot menu, if Kidux ever "
    "fails to start. Keep it somewhere safe."
)
SHOW = N_("Show")
CHANGE_ADULT_PASSWORD = N_("Change the adult password")
CURRENT_ADULT_PASSWORD = N_("Current adult password")
NEW_ADULT_PASSWORD = N_("New adult password")
COMPUTER_LANGUAGE = N_("Language and keyboard of this computer")
SCREEN_SIZE = N_("Size of everything on the screen")
APPLIES_NEXT_START = N_("Saved. It applies the next time the screen starts.")
#: On the sign-in screen, which starts again when the panel closes.
APPLIES_ON_CLOSE = N_("Saved. It applies when you close the panel.")
#: The System page's row for a computer left alone (D67).
LEFT_ALONE = N_("Left alone")
LOCK_AFTER = N_("Lock after")
SCREEN_OFF_AFTER = N_("screen off after")
MINUTES_SHORT = N_("min")
IDLE_SAVED = N_("Saved. This panel closes after that long from now on, and a child's "
                "screen locks after it from the child's next sign-in.")
PANEL_CLOSED = N_("The adult panel has closed. Open it again with the adult password.")

# --- the versions -------------------------------------------------------------

#: Under the children and under the lock screen's logo, small: what an adult
#: reads to know an update arrived. "Kidux" is the name, never translated.
KIDUX_VERSION = N_("Kidux {version}")
#: The parts of Kidux the System page lists under its version, each with its
#: own (D61's list of 2026-09-28), in an adult's words.
PART_SERVICE = N_("service")
PART_SESSION = N_("session")
PART_CHILD_SCREEN = N_("child's screen")
PART_SIGN_IN_SCREEN = N_("sign-in screen")
PART_COMMON = N_("common parts")
PART_WEB_MODULES = N_("web modules")
#: A module's version, beside its ages on the Modules page.
MODULE_VERSION = N_("version {version}")

# --- the panel's Network page (D62) --------------------------------------------

NETWORK = N_("Network")
#: Each interface on a line: what it is, then the network, the signal and the
#: address when there are.
CONNECTION = N_("Connection")
WIFI = N_("Wi-Fi")
CABLE = N_("Cable")
OTHER_CONNECTION = N_("Other")
NOT_CONNECTED = N_("Not connected")
#: The router, the machine the connection goes through, pinged once.
ROUTER = N_("Router")
ROUTER_ANSWERS = N_("It answers.")
ROUTER_SILENT = N_("It does not answer.")
ROUTER_CHECKING = N_("Asking it…")
NO_ROUTER = N_("There is none: this computer is not connected to a network.")
LOOK_AGAIN = N_("Look again")
WIFI_NETWORKS = N_("Wi-Fi networks")
NO_WIFI_IN_REACH = N_("No Wi-Fi network is in reach.")
CONNECT = N_("Connect")
FORGET = N_("Forget")
CONNECTED = N_("Connected")
WIFI_PASSWORD = N_("The network's password")
#: A network Kidux cannot join from here: an office's, which asks for a user
#: and a password of its own, or one with the old WEP.
WIFI_UNSUPPORTED = N_("Kidux cannot join this one from here.")
#: A Wi-Fi the Debian installer set up, which NetworkManager leaves alone.
WIFI_SET_AT_INSTALL = N_(
    "This computer's Wi-Fi was set up when Debian was installed, so it cannot be "
    "changed here. The user guide says how to make it changeable from this page.")
NETWORK_CHANGE_NOTE = N_(
    "Changing the network can leave the children's modules without a "
    "connection for a moment.")
CONNECTING = N_("Connecting…")
WIFI_CONNECTED = N_("Connected.")
WIFI_WRONG_PASSWORD = N_("That is not the network's password.")
WIFI_NOT_CONNECTED = N_("It did not connect.")
WIFI_PASSWORD_LENGTH = N_("A Wi-Fi password has 8 to 63 characters.")
WIFI_FORGOTTEN = N_("Forgotten. This computer no longer joins it by itself.")
FORGET_WIFI_QUESTION = N_(
    "Forget {name}? This computer will leave it now, and not join it again by "
    "itself.")
NETWORK_BUSY = N_("The network is busy. Try again in a moment.")
