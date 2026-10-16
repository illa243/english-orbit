import sys, os, argparse, traceback, logging
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
from PySide6.QtCore import QTimer, QLockFile
from core import ROOT, Store
from ui import MainWindow, ProfileDialog, STYLE, app_icon

def create_window(store, start_services=True, dialog_factory=None, window_factory=None):
    # No tray, capture, scheduler, or chat window exists until onboarding succeeds.
    first=not store.get('onboarded')
    if first:
        dialog=(dialog_factory or ProfileDialog)(first=True,store=store)
        if dialog.exec()!=QDialog.Accepted or not store.get('onboarded'):
            return None
    window=(window_factory or MainWindow)(store,start_services=start_services)
    if first and start_services:window.set_autostart(store.get('autostart'))
    return window

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tray',action='store_true');parser.add_argument('--smoke',action='store_true');parser.add_argument('--screenshot');parser.add_argument('--demo',action='store_true');parser.add_argument('--settings',action='store_true');args=parser.parse_args()
    data=ROOT/('test-output' if args.smoke or args.demo else 'data');data.mkdir(parents=True,exist_ok=True)
    (ROOT/'cache/tmp').mkdir(parents=True,exist_ok=True)
    os.environ['TEMP']=str(ROOT/'cache/tmp');os.environ['TMP']=str(ROOT/'cache/tmp')
    logging.basicConfig(filename=data/'app.log',level=logging.INFO,encoding='utf-8',format='%(asctime)s %(levelname)s %(message)s')
    app=QApplication(sys.argv);app.setApplicationName('English Orbit');app.setOrganizationName('EnglishOrbit');app.setStyle('Fusion');app.setStyleSheet(STYLE);app.setWindowIcon(app_icon());app.setQuitOnLastWindowClosed(False)
    def exception(typ,value,tb):logging.error('Unhandled error',exc_info=(typ,value,tb));print(''.join(traceback.format_exception(typ,value,tb)),file=sys.stderr)
    sys.excepthook=exception
    lock=QLockFile(str(data/'app.lock'));lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(None,'English Orbit','English Orbit РІР¶Рµ РїСЂР°С†СЋС”. Р’С–РґРєСЂРёР№ С–РєРѕРЅРєСѓ РІ СЃРёСЃС‚РµРјРЅРѕРјСѓ С‚СЂРµС—.');return 0
    store=Store(data/'orbit.sqlite')
    if args.demo:
        store.set('onboarded',True);store.set('name','Learner');store.set('level','B1');store.set('goal','РЁРІРёРґРєРѕ Р±СѓРґСѓРІР°С‚Рё РїСЂР°РІРёР»СЊРЅС– СЂРµС‡РµРЅРЅСЏ РІ СЂРѕР·РјРѕРІС–.')
        if not store.rows('SELECT id FROM messages'):
            store.add_message('mia','assistant','What is one small thing you would like to change about your evenings?')
            store.add_message('mia','user',"I decided listen to English songs, so I can enjoy music and improve my English.",corrections='{"errors":[{"before":"decided listen","after":"decided to listen","explanation":"РџС–СЃР»СЏ decide РІРёРєРѕСЂРёСЃС‚РѕРІСѓС”РјРѕ to + РґС–С”СЃР»РѕРІРѕ."}],"patterns":[{"pattern":"decide to do something","explanation":"РџС–СЃР»СЏ decide вЂ” С–РЅС„С–РЅС–С‚РёРІ С–Р· to.","example":"I decided to read every evening."}]}')
            store.add_message('mia','assistant',"That sounds like a nice way to bring English into something you already enjoy. What kind of music do you usually listen to?")
            store.save_text('chatgpt.com','I had spent a few hours a day by listening to music. Eventually, I decided listen to English songs.',final=True)
            store.add_patterns([{'pattern':'decide to do something','explanation':'РџС–СЃР»СЏ decide РІРёРєРѕСЂРёСЃС‚РѕРІСѓС”РјРѕ С–РЅС„С–РЅС–С‚РёРІ С–Р· to.','example':'I decided to read every evening.'}])
            store.add_word(store.dictionary('Everyday English'),'genuinely','С‰РёСЂРѕ, СЃРїСЂР°РІРґС–',"I'm genuinely happy for you.")
    if args.smoke:store.set('onboarded',True)
    window=create_window(store,start_services=not(args.smoke or args.demo))
    if window is None:return 0
    if args.demo:window.navigate('chats','mia')
    if args.settings:QTimer.singleShot(0,window.show_settings)
    if not args.tray or not store.get('onboarded'):window.show()
    if args.smoke or args.screenshot:
        def finish():
            if args.screenshot:window.grab().save(args.screenshot)
            print('QT_SMOKE_OK',flush=True);window.quit()
        QTimer.singleShot(1600,finish)
    return app.exec()

if __name__=='__main__':sys.exit(main())
