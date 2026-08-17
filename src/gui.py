from __future__ import annotations
import logging, os, threading, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from . import __version__
from .config import SETTINGS, with_credentials
from .credentials import clear_credentials, load_credentials, save_credentials
from .metadata import METADATA_FIELDS, field_label
from .ncbi import NCBIClient
from .output import export_results
from .scanner import build_query, scan_history, validate_lengths

BLUE, RED = "#000C66", "#D10000"


class App:
    def __init__(self, root: tk.Tk):
        self.root=root; root.title(f"Sticky MetaFASTA v{__version__}"); root.geometry("1280x720"); root.minsize(1050,650)
        email,key=load_credentials(); self.result=None; self.stop_requested=False; self.last_folder=None
        self.email=tk.StringVar(value=email or SETTINGS.email); self.key=tk.StringVar(value=key or SETTINGS.api_key)
        self.save=tk.BooleanVar(value=bool(email)); self.query=tk.StringVar(); self.organism=tk.StringVar()
        self.minimum=tk.StringVar(); self.maximum=tk.StringVar(); self.rule=tk.StringVar(value="all")
        self.location=tk.StringVar(value=str(Path.cwd()/"Results")); self.status=tk.StringVar(value="Ready")
        self.fields={k:tk.BooleanVar() for k in METADATA_FIELDS}; self._build(); root.protocol("WM_DELETE_WINDOW",self._close)

    def _build(self):
        menu=tk.Menu(self.root); settings=tk.Menu(menu,tearoff=False); help_menu=tk.Menu(menu,tearoff=False)
        settings.add_command(label="Clear saved credentials",command=self._clear_credentials)
        help_menu.add_command(label="Citations and acknowledgements",command=self._show_citations)
        help_menu.add_command(label="About Sticky MetaFASTA",command=lambda:messagebox.showinfo("About",f"Sticky MetaFASTA v{__version__}\nNCBI metadata scanner & FASTA downloader\n\nSticky Ends Bio Private Limited\nGNU GPL-3.0-or-later"))
        menu.add_cascade(label="Settings",menu=settings); menu.add_cascade(label="Help",menu=help_menu); self.root.config(menu=menu)
        head=tk.Frame(self.root,bg=BLUE,padx=18,pady=9); head.pack(fill="x")
        tk.Label(head,text="Sticky MetaFASTA",bg=BLUE,fg="white",font=("Segoe UI",24,"bold")).pack(anchor="w")
        tk.Label(head,text="NCBI metadata scanner & FASTA downloader",bg=BLUE,fg="white",font=("Segoe UI",11)).pack(anchor="w")
        tk.Label(head,text="Sticky Ends Bio Private Limited, Kannur, Kerala, India | www.stickyendsbio.com | Feedback: stickyendsbio@gmail.com",bg=BLUE,fg="white").pack(anchor="w")
        self.tabs=ttk.Notebook(self.root); self.setup=ttk.Frame(self.tabs,padding=12); self.results=ttk.Frame(self.tabs,padding=12)
        self.tabs.add(self.setup,text="Search and scan"); self.tabs.add(self.results,text="Scan results"); self.tabs.pack(fill="both",expand=True)
        cred=ttk.LabelFrame(self.setup,text="NCBI credentials",padding=8); cred.pack(fill="x")
        ttk.Label(cred,text="Email ID").grid(row=0,column=0); ttk.Entry(cred,textvariable=self.email,width=45).grid(row=0,column=1,padx=6,sticky="ew")
        ttk.Label(cred,text="API key (optional)").grid(row=0,column=2); ttk.Entry(cred,textvariable=self.key,show="•",width=40).grid(row=0,column=3,padx=6,sticky="ew")
        ttk.Checkbutton(cred,text="Save credentials in this Windows user profile",variable=self.save).grid(row=1,column=1,columnspan=3,sticky="w")
        cred.columnconfigure(1,weight=1); cred.columnconfigure(3,weight=1)
        search=ttk.LabelFrame(self.setup,text="Query and nucleotide length",padding=8); search.pack(fill="x",pady=7)
        for i,(label,var) in enumerate([("Query / search term",self.query),("Organism (optional)",self.organism),("Minimum length, nt",self.minimum),("Maximum length, nt",self.maximum)]):
            ttk.Label(search,text=label).grid(row=i//2,column=(i%2)*2,sticky="w"); ttk.Entry(search,textvariable=var).grid(row=i//2,column=(i%2)*2+1,padx=6,pady=3,sticky="ew")
        search.columnconfigure(1,weight=1); search.columnconfigure(3,weight=1)
        meta=ttk.LabelFrame(self.setup,text="Metadata fields",padding=8); meta.pack(fill="x")
        for i,(key,var) in enumerate(self.fields.items()): ttk.Checkbutton(meta,text=field_label(key),variable=var).grid(row=i//4,column=i%4,sticky="w",padx=8,pady=2)
        ttk.Button(meta,text="Select all",command=lambda:[v.set(True) for v in self.fields.values()]).grid(row=3,column=0)
        ttk.Button(meta,text="Clear all",command=lambda:[v.set(False) for v in self.fields.values()]).grid(row=3,column=1)
        rules=ttk.LabelFrame(self.setup,text="Include sequences containing",padding=8); rules.pack(fill="x",pady=7)
        ttk.Radiobutton(rules,text="All selected metadata fields",variable=self.rule,value="all").pack(side="left",padx=8)
        ttk.Radiobutton(rules,text="At least one selected metadata field",variable=self.rule,value="any").pack(side="left",padx=20)
        loc=ttk.Frame(self.setup); loc.pack(fill="x"); ttk.Label(loc,text="Results location").pack(side="left")
        ttk.Entry(loc,textvariable=self.location).pack(side="left",fill="x",expand=True,padx=6)
        ttk.Button(loc,text="Browse",command=self._browse).pack(side="left")
        buttons=ttk.Frame(self.setup); buttons.pack(fill="x",pady=8)
        self.scan=tk.Button(buttons,text="SCAN",bg=BLUE,fg="white",font=("Segoe UI",12,"bold"),padx=35,command=self._start); self.scan.pack(side="left")
        self.stop=tk.Button(buttons,text="Stop safely",bg=RED,fg="white",padx=18,state="disabled",command=self._stop); self.stop.pack(side="left",padx=7)
        ttk.Label(buttons,textvariable=self.status).pack(side="left",padx=8)
        self.progress=ttk.Progressbar(self.setup,mode="indeterminate"); self.progress.pack(fill="x")
        self.progress_text=ttk.Label(self.setup,text="Enter settings and select metadata fields."); self.progress_text.pack(anchor="w",pady=4)
        cards=ttk.Frame(self.results); cards.pack(fill="x"); self.cards={}
        for key,label in [("matches","NCBI matches"),("inspected","Length-eligible"),("excluded","Length-excluded"),("all","All fields"),("any","At least one"),("qualified","Qualifying")]:
            f=ttk.LabelFrame(cards,text=label,padding=7); f.pack(side="left",fill="x",expand=True,padx=2); self.cards[key]=ttk.Label(f,text="0",font=("Segoe UI",14,"bold")); self.cards[key].pack()
        rr=ttk.Frame(self.results); rr.pack(fill="x",pady=8); ttk.Label(rr,text="Current matching rule:").pack(side="left")
        ttk.Radiobutton(rr,text="All selected fields",variable=self.rule,value="all",command=self._refresh).pack(side="left",padx=8)
        ttk.Radiobutton(rr,text="At least one selected field",variable=self.rule,value="any",command=self._refresh).pack(side="left",padx=8)
        self.table=ttk.Treeview(self.results,columns=("field","available","missing","pct"),show="headings",height=9)
        for col,text in [("field","Metadata field"),("available","Available"),("missing","Missing"),("pct","Availability %")]: self.table.heading(col,text=text)
        self.table.column("field",width=320); self.table.pack(fill="both",expand=True)
        self.preview=ttk.Treeview(self.results,columns=("version","organism","length","category"),show="headings",height=6)
        for col,text in [("version","Accession"),("organism","Organism"),("length","Length"),("category","Reference category")]: self.preview.heading(col,text=text)
        self.preview.column("organism",width=260); self.preview.column("category",width=230); self.preview.pack(fill="both",expand=True,pady=(7,0))
        dl=ttk.Frame(self.results); dl.pack(fill="x",pady=8); self.limit=tk.StringVar()
        ttk.Label(dl,text="FASTA quantity (blank = all)").pack(side="left"); ttk.Entry(dl,textvariable=self.limit,width=12).pack(side="left",padx=5)
        ttk.Button(dl,text="Download CSV report",command=lambda:self._export(False)).pack(side="left",padx=5)
        ttk.Button(dl,text="Download FASTA + data",command=lambda:self._export(True)).pack(side="left",padx=5)

    def _browse(self):
        value=filedialog.askdirectory(initialdir=self.location.get())
        if value:self.location.set(value)

    def _clear_credentials(self):
        if messagebox.askyesno("Clear saved credentials","Remove the saved NCBI email ID and API key from this Windows profile?"):
            clear_credentials(); self.email.set(""); self.key.set(""); self.save.set(False)

    def _show_citations(self):
        text=("Scientific resources\nNCBI; GenBank and NCBI Nucleotide; Entrez Programming Utilities.\n\n"
              "Software\nPython; Biopython (Cock et al., Bioinformatics 2009, DOI: 10.1093/bioinformatics/btp163); Tcl/Tk; PyInstaller.\n\n"
              "Sticky MetaFASTA is independently developed and is not affiliated with, sponsored by, or endorsed by NCBI. "
              "See CITATIONS.md distributed with the application for complete citations and acknowledgements.")
        window=tk.Toplevel(self.root); window.title("Citations and acknowledgements"); window.geometry("720x420")
        box=tk.Text(window,wrap="word",padx=14,pady=14); box.insert("1.0",text); box.config(state="disabled"); box.pack(fill="both",expand=True)
        ttk.Button(window,text="Close",command=window.destroy).pack(pady=8)

    def _start(self):
        try:
            if "@" not in self.email.get(): raise ValueError("Enter a valid NCBI email ID.")
            self.search_term=self.query.get().strip(); self.organism_text=self.organism.get().strip(); self.full_query=build_query(self.search_term,self.organism_text)
            self.min_value=int(self.minimum.get()) if self.minimum.get().strip() else None; self.max_value=int(self.maximum.get()) if self.maximum.get().strip() else None
            validate_lengths(self.min_value,self.max_value); self.selected=[k for k,v in self.fields.items() if v.get()]
            if not self.selected: raise ValueError("Select at least one metadata field.")
            Path(self.location.get()).mkdir(parents=True,exist_ok=True)
        except (ValueError,OSError) as exc: messagebox.showerror("Check settings",str(exc)); return
        if self.save.get(): save_credentials(self.email.get(),self.key.get())
        self.stop_requested=False; self.scan.config(state="disabled"); self.stop.config(state="normal"); self.progress.start(12); self.status.set("Checking NCBI matches...")
        threading.Thread(target=self._worker,daemon=True).start()

    def _worker(self):
        logger=logging.getLogger("sticky_metafasta_gui"); logger.addHandler(logging.NullHandler())
        try:
            settings=with_credentials(SETTINGS,self.email.get(),self.key.get()); client=NCBIClient(settings,logger,status_callback=lambda m:self.root.after(0,self._message,m))
            history=client.search_history(self.full_query)
            if not history.count: raise ValueError("No exact matches were found in NCBI.")
            warning="\nThis is a large dataset." if history.count>=settings.large_warning_threshold else ""
            if not messagebox.askyesno("Confirm NCBI scan",f"Final query:\n{self.full_query}\n\nNCBI matches: {history.count:,}{warning}\n\nContinue?"): return
            self.result=scan_history(client=client,history=history,settings=settings,query=self.full_query,selected_fields=self.selected,
                minimum_length=self.min_value,maximum_length=self.max_value,logger=logger,progress_callback=lambda r:self.root.after(0,self._show_progress,r),should_stop=lambda:self.stop_requested)
            self.root.after(0,self._complete)
        except Exception as exc:self.root.after(0,messagebox.showerror,"Scan could not be completed",str(exc))
        finally:self.root.after(0,self._reset)

    def _message(self,text): self.progress_text.config(text=text)
    def _show_progress(self,r):
        q=r.all_count if self.rule.get()=="all" else r.any_count; self._message(f"Fetched {r.fetched:,}/{r.total_matches:,} | Inspected {r.inspected:,} | Length-excluded {r.length_excluded:,} | Qualifying {q:,}")
    def _stop(self): self.stop_requested=True; self.status.set("Stopping safely after the current request...")
    def _reset(self): self.progress.stop(); self.scan.config(state="normal"); self.stop.config(state="disabled")
    def _complete(self): self._refresh(); self.tabs.select(self.results); self.status.set("Partial scan available" if self.result.interrupted else "Scan completed")
    def _refresh(self):
        if not self.result:return
        r=self.result; values={"matches":r.total_matches,"inspected":r.inspected,"excluded":r.length_excluded,"all":r.all_count,"any":r.any_count,"qualified":r.all_count if self.rule.get()=="all" else r.any_count}
        for key,value in values.items():self.cards[key].config(text=f"{value:,}")
        self.table.delete(*self.table.get_children())
        for f in r.selected_fields:
            available=r.availability[f]; pct=available*100/r.inspected if r.inspected else 0; self.table.insert("","end",values=(field_label(f),available,r.inspected-available,f"{pct:.2f}"))
        self.preview.delete(*self.preview.get_children())
        for row in r.qualifying_rows(self.rule.get())[:100]:
            self.preview.insert("","end",values=(row["Version"],row["Organism"],row["Sequence_Length"],row["Reference_Category"]))
    def _export(self,fasta):
        try: limit=int(self.limit.get()) if self.limit.get().strip() else None
        except ValueError: messagebox.showerror("Check quantity","Enter a positive whole number or leave blank."); return
        if limit is not None and limit<=0: messagebox.showerror("Check quantity","Enter a positive whole number or leave blank."); return
        self.last_folder=export_results(self.result,rule=self.rule.get(),base_dir=Path(self.location.get()),query_term=self.search_term,include_fasta=fasta,
            limit=limit if fasta else None,search_term=self.search_term,organism=self.organism_text,minimum_length=self.min_value,maximum_length=self.max_value,
            api_key_used=bool(self.key.get()),status="Safely stopped - partial results" if self.result.interrupted else "Completed")
        messagebox.showinfo("Results saved",f"Results were saved to:\n{self.last_folder}")
    def _close(self):
        if self.stop["state"]=="normal" and not messagebox.askyesno("Stop safely?","A scan is running. Stop safely and close?"):return
        self.stop_requested=True; self.root.destroy()


def main():
    root=tk.Tk(); App(root); root.mainloop()


if __name__=="__main__":main()
