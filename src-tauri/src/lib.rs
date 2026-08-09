use std::process::Command;
use std::thread;
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager,
};


#[tauri::command]
fn get_backend_status() -> String {
    "Transcribe AI Backend Operational".to_string()
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Spawn background Python backend server if not already running
            thread::spawn(|| {
                let home = std::env::var("HOME").unwrap_or_default();
                let home_local_agent = format!("{}/.local/bin/neural-agent", home);
                let home_local_py = format!("{}/.local/bin/python3", home);

                let candidates: Vec<(String, Vec<&str>)> = vec![
                    ("/Volumes/personal/programmingFolders/transcribe/.venv/bin/neural-agent".to_string(), vec!["serve", "--port", "8000"]),
                    ("/Volumes/personal/programmingFolders/transcribe/.venv/bin/python3".to_string(), vec!["-m", "neural_agent_os.cli.main", "serve", "--port", "8000"]),
                    (home_local_agent, vec!["serve", "--port", "8000"]),
                    (home_local_py, vec!["-m", "neural_agent_os.cli.main", "serve", "--port", "8000"]),
                    ("/opt/homebrew/bin/neural-agent".to_string(), vec!["serve", "--port", "8000"]),
                    ("/opt/homebrew/bin/python3".to_string(), vec!["-m", "neural_agent_os.cli.main", "serve", "--port", "8000"]),
                    ("/usr/local/bin/neural-agent".to_string(), vec!["serve", "--port", "8000"]),
                    ("/usr/local/bin/python3".to_string(), vec!["-m", "neural_agent_os.cli.main", "serve", "--port", "8000"]),
                    ("neural-agent".to_string(), vec!["serve", "--port", "8000"]),
                    ("python3".to_string(), vec!["-m", "neural_agent_os.cli.main", "serve", "--port", "8000"]),
                ];

                for (cmd, args) in candidates {
                    if let Ok(mut child) = Command::new(&cmd).args(&args).spawn() {
                        let _ = child.wait();
                        break;
                    }
                }
            });

            // System Tray Menu for macOS / Windows / Linux
            let quit_i = MenuItem::with_id(app, "quit", "Quit Neural Agent OS", true, None::<&str>)?;
            let show_i = MenuItem::with_id(app, "show", "Open Dashboard", true, None::<&str>)?;
            let tray_menu = Menu::with_items(app, &[&show_i, &quit_i])?;

            let _tray = TrayIconBuilder::new()
                .menu(&tray_menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .build(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_backend_status])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
