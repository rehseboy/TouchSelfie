'''
Open source photo booth.

Kevin Osborn and Justin Shaw
WyoLum.com
'''

## imports
from tkkb import Tkkb
import signal
import time
from Tkinter import *
import tkMessageBox
import ImageTk
from mailfile import *
import custom
import Image
import config
from constants import *
### booth cam may need to present a file dialog gui.  So import after root is defined.
from boothcam import *

IMAGE_2_PATH = '/home/pi/Downloads/1-2-stars-picture.png'

IMAGE_1_PATH = '/home/pi/Downloads/BG-AM.png'

BG_COLOR = '#000080'
FG_COLOR = '#D4AF37'


def screenshot(*args):
    import screenshot
    screenshot.snap()

def interrupted(signum, frame):
    "called when serial read times out"
    print 'interrupted!'
    signal.signal(signal.SIGALRM, interrupted)


def display_image(im=None):
    '''
    display image im in GUI window
    '''
    global image_tk

    x, y = im.size
    x = int(x / SCALE)
    y = int(y / SCALE)

    im = im.resize((x, y));
    image_tk = ImageTk.PhotoImage(im)

    ## delete all canvas elements with "image" in the tag
    can.delete("image")
    can.create_image([(WIDTH + x) / 2 - x / 2,
                      0 + y / 2],
                     image=image_tk,
                     tags="image")


def timelapse_due():
    '''
    Return true if a time lapse photo is due to be taken (see custom.TIMELAPSE)
    '''
    if custom.TIMELAPSE > 0:
        togo = custom.TIMELAPSE - (time.time() - last_snap)
        out = togo < 0
    else:
        out = False
    return out


def refresh_oauth2_credentials():
    if custom.SIGN_ME_IN:
        if setup_google():
            print 'refreshed!', custom.oauth2_refresh_period
        else:
            print 'refresh failed'
        root.after(custom.oauth2_refresh_period, refresh_oauth2_credentials)


def check_and_snap(force=False, countdown1=None, email=None):
    '''
    Check button status and snap a photo if button has been pressed.

    force -- take a snapshot regarless of button status
    countdown1 -- starting value for countdown timer
    '''
    global image_tk, Button_enabled, last_snap, signed_in

    if email is not None:
        print 'Inside snap with email %s' % email.get()
    else:
        print 'Inside snap without email'

    if countdown1 is None:
        countdown1 = custom.countdown1
    # if signed_in:
    #     send_button.config(state=NORMAL)
    #     etext.config(state=NORMAL)
    # else:
    #     send_button.config(state=DISABLED)
    #     etext.config(state=DISABLED)
    if (Button_enabled == False):
        ## inform alamode that we are ready to receive button press events
        ## ser.write('e') #enable button (not used)
        Button_enabled = True
        # can.delete("text")
        # can.create_text(WIDTH/2, HEIGHT - STATUS_H_OFFSET, text="Press button when ready", font=custom.CANVAS_FONT, tags="text")
        # can.update()

        ## get command string from alamode
    #    command = ser.readline().strip()
    command = ""
    if Button_enabled and (force or command == "snap" or timelapse_due()):
        ## take a photo and display it
        Button_enabled = False
        can.delete("text")
        can.update()

        if timelapse_due():
            countdown1 = 0
        im = snap(can, countdown1=countdown1, effect='None')
        #        setLights(r_var.get(), g_var.get(), b_var.get())
        if im is not None:
            if custom.TIMELAPSE > 0:
                togo = custom.TIMELAPSE - (time.time() - last_snap)
            else:
                togo = 1e8
            last_snap = time.time()
            display_image(im)
            can.delete("text")
            can.create_text(WIDTH / 2, HEIGHT - STATUS_H_OFFSET, text="Uploading Image", font=custom.CANVAS_FONT,
                            tags="text")
            can.update()
            if signed_in:
                if custom.albumID == 'None':
                    global albumID_informed
                    if not albumID_informed:
                        tkMessageBox.showinfo(
                            'Album ID not set',
                            'Click Customize to select albumID',
                            parent=root
                        )
                        albumID_informed = True
                else:
                    try:
                        googleUpload(custom.PROC_FILENAME)
                        if email is not None:
                            sendPic(email.get())
                    except Exception, e:
                        tkMessageBox.showinfo("Upload Error", str(e) +
                                              '\nUpload Failed:%s' % e)

                        # signed_in = False
            can.delete("text")
            # can.create_text(WIDTH/2, HEIGHT - STATUS_H_OFFSET, text="Press button when ready", font=custom.CANVAS_FONT, tags="text")
            can.update()
    else:
        ### what command did we get?
        if command.strip():
            print command
    if not force:
        ## call this function again in 100 ms
        root.after_id = root.after(100, check_and_snap)


def on_close(*args, **kw):
    '''
    when window closes cancel pending root.after() call
    '''
    if root.after_id is not None:
        root.after_cancel(root.after_id)

    ### turn off LEDs
    r_var.set(0)
    g_var.set(0)
    b_var.set(0)
    root.quit()


def force_snap(countdown1=None):
    if countdown1 is None:
        countdown1 = custom.countdown1
    check_and_snap(force=True, countdown1=countdown1,email=email_addr)

#
# def delay_timelapse(*args):
#     '''
#     Prevent a timelapse snapshot when someone is typeing an email address
#     '''
#     global last_snap
#     last_snap = time.time()


## send RGB changes to alamode
def on_rgb_change(*args):
    setLights(r_var.get(), g_var.get(), b_var.get())


def labeled_slider(parent, label, from_, to, side, variable):
    frame = Frame(parent)
    Label(frame, text=label).pack(side=TOP)
    scale = Scale(frame, from_=from_, to=to, variable=variable, resolution=1).pack(side=TOP)
    frame.pack(side=side)
    return scale


def snap_callback(*args):
    force_snap()

# if they enter an email address send photo. add error checking
def sendPic(email):
    if signed_in:
        print 'sending photo by email to %s' % email
        try:
            sendMail(email.strip(),
                     custom.emailSubject,
                     custom.emailMsg,
                     custom.PROC_FILENAME)

        except Exception, e:
            print 'Send Failed::', e
            can.delete("all")
            can.create_text(WIDTH / 2, HEIGHT - STATUS_H_OFFSET, text="Send Failed", font=custom.CANVAS_FONT,
                            tags="text")
            can.update()
            time.sleep(1)
            can.delete("all")
            im = Image.open(custom.PROC_FILENAME)
            display_image(im)
            can.create_text(WIDTH / 2, HEIGHT - STATUS_H_OFFSET, text="Press button when ready",
                            font=custom.CANVAS_FONT, tags="text")
            can.update()
    else:
        print 'Not signed in'


def entry_point(master):
    global email_addr
    self = Toplevel(master)
    self.geometry("%dx%d%+d%+d" % (WIDTH, 400, 0, 40))
    self.config(bg=BG_COLOR)
    # self.overrideredirect(1)
    # self.master = master
    email_addr = StringVar()

    def set_email_and_start():
        print 'Starting with email %s' % email_addr.get()
        close()
        check_and_snap(force=True, countdown1=custom.countdown1, email=email_addr)

    def close_and_start():
        print 'Starting without email'
        email_addr = None
        close()
        check_and_snap(force=True, countdown1=custom.countdown1)

    def close():
        self.destroy()

    def launch_tkkb(*args):
        '''
        Launch on screen keyboard program called tkkb-keyboard.
        install with '$ sudo apt-get install tkkb-keyboard'
        '''
        global tkkb
        if tkkb is None:
            tkkb = Toplevel(self)

            def onEnter(*args):
                kill_tkkb()
                set_email_and_start()

            Tkkb(tkkb, etext, onEnter=onEnter)
            etext.config(state=NORMAL)
            tkkb.wm_attributes("-topmost", 1)
            tkkb.transient(self)
            tkkb_button.config(command=kill_tkkb, text="Close KB")
            tkkb.protocol("WM_DELETE_WINDOW", kill_tkkb)

    def kill_tkkb():
        '''
        Delete on screen keyboard program called tkkb-keyboard.
        '''
        global tkkb
        if tkkb is not None:
            tkkb.destroy()
            try:
                tkkb_button.config(command=launch_tkkb, text="Open KB")
                tkkb = None
            except:
                pass

    def get_resized(path):
        photo = Image.open(path)
        width, height = photo.size
        if SCREEN_W / width < SCREEN_H / height:
            scale = (.25 * SCREEN_W) / width
        else:
            scale = (.25 * SCREEN_H) / height
        photo = photo.resize((int(width * scale), int(height * scale)))
        return ImageTk.PhotoImage(photo)

    def set_bg(button):
        if button == 1:
            on = b1
            off = b2
            path = IMAGE_1_PATH
        else:
            on = b2
            off = b1
            path = IMAGE_2_PATH

        on.config(bg=FG_COLOR,activebackground=FG_COLOR)
        off.config(bg=BG_COLOR)
        custom.set_logo(path)


    frame = Frame(self)
    tkkb_button = Button(frame, command=launch_tkkb, text="Launch-KB")
    # tkkb_button.pack(side=LEFT)
    send_button = Button(frame, text="Set Email & Start", command=set_email_and_start, font=custom.BUTTON_FONT, bg=BG_COLOR)
    send_button.pack(side=RIGHT)

    ## add a text entry box for email addresses
    etext = Entry(frame, width=40, textvariable=email_addr, font=custom.BUTTON_FONT)
    etext.pack()
    frame.pack()
    next_frame = Frame(self)
    Button(next_frame, command=close_and_start, text="Start (Don't Set Email)", font=custom.BUTTON_FONT, bg=BG_COLOR).pack(side=RIGHT)
    next_frame.pack()
    etext.bind('<Button-1>', launch_tkkb)

    if not signed_in:
        send_button.config(state=DISABLED)
        etext.config(state=DISABLED)

    etext.focus_set()

    images_frame = Frame(self)
    image1 = get_resized(IMAGE_1_PATH)
    image2 = get_resized(IMAGE_2_PATH)
    b1 = Button(images_frame, command= lambda *args: set_bg(1))
    b1.config(image=image1)
    b1.image = image1
    b1.pack(side=LEFT)
    b2 = Button(images_frame, command= lambda *args: set_bg(2))
    b2.config(image=image2)
    b2.image = image2
    b2.pack(side=RIGHT)
    images_frame.pack()
    set_bg(1)


## This is a simple GUI, so we allow the root singleton to do the legwork
root = Tk()
root.attributes("-fullscreen", True)
root.config(bg=BG_COLOR)
root.bind('<F12>', screenshot)

## set display geometry
WIDTH = 800
HEIGHT = 480
albumID_informed = False  ### only show albumID customize info once

## set photo size to fit nicely in screen
SCALE = 1.8

## the countdown starting value
# COUNTDOWN1 = custom.countdown1 ### use custom.countdown1 reference directly

## put the status widget below the displayed image
STATUS_H_OFFSET = 150  ## was 210

## only accept button inputs from the AlaMode when ready
Button_enabled = False

TIMEOUT = .3  # number of seconds your want for timeout

last_snap = time.time()

tkkb = None

## for clean shutdowns
root.after_id = None

root.protocol('WM_DELETE_WINDOW', on_close)

# bound to text box for email
# send_email = False
email_addr = None
# email_addr.trace('w', delay_timelapse)

## bound to RGB sliders
r_var = IntVar()
g_var = IntVar()
b_var = IntVar()


## call on_rgb_change when any of the sliders move
r_var.trace('w', on_rgb_change)
g_var.trace('w', on_rgb_change)
b_var.trace('w', on_rgb_change)

w, h = root.winfo_screenwidth(), root.winfo_screenheight()

# root.overrideredirect(1)
root.geometry("%dx%d+0+0" % (WIDTH, HEIGHT))
root.focus_set()  # <-- move focus to this widget

frame = Frame(root)
Button(frame, text="Again!", command=force_snap, font=custom.BUTTON_FONT,bg=BG_COLOR).pack(side=LEFT)
Button(frame, text="All Done!", command=lambda *args: entry_point(root), font=custom.BUTTON_FONT, bg=BG_COLOR).pack(side=RIGHT)
frame.pack()
# Button(frame, text="Exit", command=on_close).pack(side=LEFT)
# Button(frame, text="Customize", command=lambda *args: custom.customize(root)).pack(side=LEFT)


## add a software button in case hardware button is not available
interface_frame = Frame(root)

snap_button = Button(interface_frame, text="snap", command=force_snap, font=custom.BUTTON_FONT)
# snap_button.pack(side=RIGHT) ## moved to canvas
interface_frame.pack(side=RIGHT)

## the canvas will display the images
can = Canvas(root, width=WIDTH, height=HEIGHT)
can.pack()

# can.bind('<Button-1>', snap_callback)

## sign in to google?
if custom.SIGN_ME_IN:
    signed_in = setup_google()
else:
    signed_in = False

### take the first photo (no delay)
can.delete("text")
can.create_text(WIDTH / 2, HEIGHT / 2, text="SMILE ;-)", font=custom.CANVAS_FONT, tags="splash")
# can.updater()
force_snap(countdown1=0)

### check button after waiting for 200 ms
# root.after(200, check_and_snap)
if custom.SIGN_ME_IN:
    root.after(custom.oauth2_refresh_period, refresh_oauth2_credentials)
root.wm_title("Asja & Michael's Photobooth")

on_rgb_change()
entry_point(master=root)
root.mainloop()
