import os
import time
import traceback
from tkinter import *
from tkinter import filedialog
from scraper import Scraper

class Window(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.title("CopperKeep")
        self.option_add("*Font", ("TkDefaultFont", 11))

        f1 = Frame(self); f1.pack(fill=X, padx=10, pady=5)
        f2 = Frame(self); f2.pack(fill=X, padx=10, pady=5)
        f3 = Frame(self); f3.pack(fill=X, padx=10, pady=5)

        Label(f1, text="Save to:", width=10, anchor=W).pack(side=LEFT)
        self.save_var = StringVar(value=os.path.abspath(os.path.dirname(__file__)))
        Entry(f1, textvariable=self.save_var, width=60).pack(side=LEFT, fill=X, expand=True, padx=4)
        Button(f1, text="Browse", command=self.browse).pack(side=LEFT)

        Label(f2, text="Gallery URL:", width=10, anchor=W).pack(side=LEFT)
        self.url_var = StringVar()
        Entry(f2, textvariable=self.url_var, width=70).pack(side=LEFT, fill=X, expand=True, padx=4)

        self.ps_var = BooleanVar()
        Checkbutton(f3, text="photoshoot folders (ps)", variable=self.ps_var).pack(side=LEFT)
        Button(f3, text="Start", width=12, command=self.start).pack(side=RIGHT, padx=5)
        Button(f3, text="Close", width=12, command=self.destroy).pack(side=RIGHT)

    def browse(self):
        path = filedialog.askdirectory()
        if path:
            self.save_var.set(path)

    def start(self):
        save_location = self.save_var.get().strip()
        start_url = self.url_var.get().strip()
        if not start_url:
            return
        # auto derive base like original Gooey version
        base_url = start_url.rsplit('/', 1)[0] + '/'
        ps = self.ps_var.get()
        self.destroy()
        scraper = Scraper(save_location, base_url)
        t0 = time.time()
        try:
            scraper.start(start_url, ps=ps)
        except Exception as e:
            print(f"\nERROR: {e}")
            traceback.print_exc()
            input("Press Enter to exit...")
            return
        print(f"\n{round(time.time()-t0)} seconds")
        print(f"{scraper.total} images")
        input("Done. Press Enter to exit...")

if __name__ == '__main__':
    Window().mainloop()
