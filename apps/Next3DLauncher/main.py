#!/usr/bin/env python3
"""Next 3D native desktop selector. NextCAD and Next BIM remain separate processes."""
from __future__ import annotations
import os, subprocess, sys, tkinter as tk
from pathlib import Path
from tkinter import messagebox
APP_ROOT = Path(__file__).resolve().parents[2]

def _candidate_paths(kind: str) -> list[Path]:
    if kind == "nextcad":
        override = os.environ.get("NEXTCAD_EXECUTABLE")
        bundled = [
            APP_ROOT/"runtime"/"NextCAD"/"FreeCAD.exe",
            APP_ROOT/"runtime"/"NextCAD"/"bin"/"FreeCAD.exe",
            APP_ROOT/"runtime"/"NextCAD"/"bin"/"FreeCAD",
            APP_ROOT/"runtime"/"NextCAD.app"/"Contents"/"MacOS"/"FreeCAD",
            APP_ROOT/"runtime"/"NextCAD"/"FreeCAD",
            APP_ROOT/"apps"/"NextCAD"/"build"/"bin"/"FreeCAD.exe",
            APP_ROOT/"apps"/"NextCAD"/"build"/"bin"/"FreeCAD",
        ]
        names = ("FreeCAD.exe", "FreeCAD", "freecad")
    elif kind == "nextbim":
        override = os.environ.get("NEXTBIM_EXECUTABLE")
        bundled = [
            APP_ROOT/"runtime"/"NextBIM"/"NextBIM.exe",
            APP_ROOT/"runtime"/"NextBIM"/"NextBIM",
            APP_ROOT/"runtime"/"NextBIM.app"/"Contents"/"MacOS"/"NextBIM",
            APP_ROOT/"apps"/"NextBIM"/"target"/"release"/"NextBIM.exe",
            APP_ROOT/"apps"/"NextBIM"/"target"/"release"/"NextBIM",
            APP_ROOT/"apps"/"NextBIM"/"target"/"release"/"bimcraft.exe",
            APP_ROOT/"apps"/"NextBIM"/"target"/"release"/"bimcraft",
        ]
        names = ("NextBIM.exe", "NextBIM", "bimcraft.exe", "bimcraft")
    else:
        raise ValueError(f"Unknown application key: {kind}")
    candidates = [Path(override).expanduser()] if override else []
    candidates.extend(bundled)
    from shutil import which
    for name in names:
        found = which(name)
        if found:
            candidates.append(Path(found))
    return candidates

def find_runtime(kind: str) -> Path | None:
    for candidate in _candidate_paths(kind):
        if candidate.is_file() and (os.name == "nt" or os.access(candidate, os.X_OK)):
            return candidate.resolve()
    return None

class Next3DLauncher:
    BG="#0b1220"; PANEL="#111c2e"; ACCENT="#4bd5c4"
    TEXT="#f2f6fc"; MUTED="#9eacc2"; BORDER="#26364d"
    def __init__(self, root: tk.Tk) -> None:
        self.root=root
        self.buttons: dict[str,tk.Button] = {}
        root.title("Next 3D"); root.configure(bg=self.BG)
        root.geometry("1120x760"); root.minsize(920,650)
        self._center(); self._build()
    def _center(self):
        self.root.update_idletasks()
        w,h=1120,760; sw,sh=self.root.winfo_screenwidth(),self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{max(0,(sw-w)//2)}+{max(0,(sh-h)//2)}")
    def _label(self,parent,text,*,size=11,color=None,bold=False,**kwargs):
        return tk.Label(parent,text=text,bg=kwargs.pop("bg",self.BG),fg=color or self.TEXT,
                        font=("Segoe UI",size,"bold" if bold else "normal"),**kwargs)
    def _build(self):
        shell=tk.Frame(self.root,bg=self.BG); shell.pack(fill="both",expand=True)
        top=tk.Frame(shell,bg="#080e19",height=72,highlightthickness=1,highlightbackground=self.BORDER)
        top.pack(fill="x"); top.pack_propagate(False)
        brand=tk.Frame(top,bg="#080e19"); brand.pack(side="left",padx=34,pady=14)
        mark=tk.Canvas(brand,width=40,height=40,bg="#080e19",highlightthickness=0); mark.pack(side="left",padx=(0,12))
        mark.create_polygon(4,34,4,8,12,8,29,27,29,8,36,8,36,34,27,34,11,16,11,34,fill=self.ACCENT,outline="")
        self._label(brand,"NEXT 3D",size=17,bold=True,bg="#080e19").pack(side="left")
        self._label(brand,"ENGINEERING WORKSPACE",size=8,color=self.MUTED,bg="#080e19").pack(side="left",padx=14,pady=(7,0))
        self._label(top,"NATIVE DESKTOP",size=9,color=self.MUTED,bg="#080e19").pack(side="right",padx=34)
        content=tk.Frame(shell,bg=self.BG); content.pack(fill="both",expand=True,padx=64,pady=(54,32))
        self._label(content,"Your engineering workspace",size=27,bold=True).pack(anchor="w")
        self._label(content,"Choose an application to continue. Each runs independently with its own native tools and project files.",
                    size=11,color=self.MUTED).pack(anchor="w",pady=(10,0))
        cards=tk.Frame(content,bg=self.BG); cards.pack(fill="both",expand=True,pady=(42,24))
        cards.grid_columnconfigure(0,weight=1,uniform="apps"); cards.grid_columnconfigure(1,weight=1,uniform="apps")
        cards.grid_rowconfigure(0,weight=1)
        self._card(cards,0,"NEXTCAD","Parametric CAD","Design with sketches, constraints, solids, surfaces and technical drawings.",
                   "2D + 3D DESIGN","Open NextCAD","nextcad")
        self._card(cards,1,"NEXT BIM","Building information modelling","Create and coordinate architectural, structural and building-services models.",
                   "BUILDING + ENGINEERING","Open Next BIM","nextbim")
        footer=tk.Frame(content,bg=self.BG); footer.pack(fill="x",pady=(6,0))
        self._label(footer,"Independent native applications  /  Separate model engines  /  Original project formats retained",
                    size=9,color=self.MUTED).pack(side="left")
        self._label(footer,"NEXT 3D  ·  DEVELOPMENT BUILD",size=8,color="#71819a").pack(side="right")
    def _card(self,parent,col,name,subtitle,description,tag,button_text,key):
        card=tk.Frame(parent,bg=self.PANEL,highlightthickness=1,highlightbackground=self.BORDER)
        card.grid(row=0,column=col,sticky="nsew",padx=(0,14) if col==0 else (14,0))
        inner=tk.Frame(card,bg=self.PANEL); inner.pack(fill="both",expand=True,padx=30,pady=28)
        glyph=tk.Canvas(inner,width=74,height=74,bg=self.PANEL,highlightthickness=0); glyph.pack(anchor="w")
        glyph.create_rectangle(2,2,72,72,outline="#33536a",width=1)
        if key=="nextcad":
            glyph.create_line(14,55,37,15,59,55,14,55,fill=self.ACCENT,width=3,joinstyle="round")
            glyph.create_line(22,43,51,43,fill="#dce9f7",width=2)
            glyph.create_line(37,15,37,63,fill="#66819b",width=1,dash=(3,3))
        else:
            glyph.create_rectangle(17,17,57,57,outline=self.ACCENT,width=3)
            glyph.create_line(17,30,57,30,fill="#dce9f7",width=2)
            glyph.create_line(31,17,31,57,fill="#dce9f7",width=2)
            glyph.create_line(43,30,43,57,fill="#66819b",width=1)
        self._label(inner,tag,size=8,color=self.ACCENT,bold=True,bg=self.PANEL).pack(anchor="w",pady=(30,8))
        self._label(inner,name,size=23,bold=True,bg=self.PANEL).pack(anchor="w")
        self._label(inner,subtitle,size=10,color="#c1cede",bg=self.PANEL).pack(anchor="w",pady=(4,0))
        self._label(inner,description,size=10,color=self.MUTED,bg=self.PANEL,justify="left",wraplength=360).pack(anchor="w",pady=(20,0))
        self._label(inner,"APPLICATION RUNTIME",size=8,color="#8193aa",bold=True,bg=self.PANEL).pack(anchor="w",pady=(36,7))
        runtime=find_runtime(key); status_text=f"Found  ·  {runtime.name}" if runtime else "Not installed in this checkout"
        status_color="#7cdbb5" if runtime else "#f0bf78"
        status=tk.Frame(inner,bg="#0b1524",padx=10,pady=9); status.pack(fill="x")
        self._label(status,"●",size=9,color=status_color,bg="#0b1524").pack(side="left")
        self._label(status,status_text,size=9,color="#c3d0df",bg="#0b1524").pack(side="left",padx=(7,0))
        btn=tk.Button(inner,text=button_text,command=lambda k=key:self.open_app(k),bg="#1b3c4f",fg=self.TEXT,
                      activebackground="#24566a",activeforeground=self.TEXT,relief="flat",bd=0,cursor="hand2",
                      font=("Segoe UI",10,"bold"),padx=16,pady=13)
        btn.pack(fill="x",pady=(22,0)); self.buttons[key]=btn
    def open_app(self,kind:str):
        runtime=find_runtime(kind); product="NextCAD" if kind=="nextcad" else "Next BIM"
        if runtime is None:
            env_var="NEXTCAD_EXECUTABLE" if kind=="nextcad" else "NEXTBIM_EXECUTABLE"
            messagebox.showwarning(f"{product} runtime not found",
                f"{product} has not been built or installed in this checkout.\n\n"
                f"Expected a packaged runtime beside Next 3D, or set {env_var} to its executable.\n\n"
                "This is a real runtime check: no placeholder application has been launched.",parent=self.root)
            return
        try:
            command=[str(runtime)]; environment=os.environ.copy(); environment["NEXT3D_HOME"]=str(APP_ROOT)
            if kind=="nextcad":
                command.append(str(APP_ROOT/"apps"/"NextCAD"/"NextCADStartup.FCMacro"))
            command.extend(sys.argv[1:]); subprocess.Popen(command,env=environment)
        except OSError as exc:
            messagebox.showerror(f"Could not start {product}",str(exc),parent=self.root)

def main()->int:
    root=tk.Tk(); Next3DLauncher(root); root.mainloop(); return 0
if __name__=="__main__":
    raise SystemExit(main())
