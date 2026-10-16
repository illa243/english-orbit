using System;
using System.IO;
using System.Diagnostics;
using System.Windows.Forms;
class Launcher {
    [STAThread] static void Main(string[] args) {
        string root=AppDomain.CurrentDomain.BaseDirectory;
        string python=Path.Combine(root,@"runtime\python\pythonw.exe");
        if(!File.Exists(python)) python=Path.Combine(root,@".qt-env\Scripts\pythonw.exe");
        if(!File.Exists(python)) { MessageBox.Show("Python runtime is missing. Run setup.ps1 in the application folder first.","English Orbit"); return; }
        var info=new ProcessStartInfo(python,"\""+Path.Combine(root,"main.py")+"\""+(Array.IndexOf(args,"--tray")>=0?" --tray":""));
        info.WorkingDirectory=root;info.UseShellExecute=false;info.CreateNoWindow=true;
        try { Process.Start(info); } catch(Exception e) { MessageBox.Show(e.Message,"English Orbit"); }
    }
}
