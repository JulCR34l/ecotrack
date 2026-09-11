# ecotrack

URL del repositorio: https://github.com/JulCR34l/ecotrack
App en producción: https://ecotrack-dhnmhzjdtfohgfu382ynw3.streamlit.app

.cursorrules:
You are an expert full-stack developer focusing on clean, modular, and modern code.
Project: EcoTrack (Carbon footprint tracker MVP via natural language input).

Rules:
- Tech Stack: Python 3 with Streamlit for web UI and pandas for data handling.
- Build a clean web application where users type daily activities in natural language (e.g., "Hoy comí carne y viaje 20km en bus") and calculate estimated CO2 footprint in kg CO2.
- Include clear visual feedback (metrics, simple charts, breakdown of activities).
- Always output complete, fully functional files (app.py, requirements.txt) without placeholders.

Vibe Report:
EcoTrack — Vibe Report
Configuración del agente

Para este proyecto configuré el archivo .cursorrules con las siguientes directrices clave: el agente debía actuar como desarrollador full-stack experto, enfocado en código limpio y modular. El stack quedó fijado en Python 3 con Streamlit para la interfaz web y pandas para el manejo de datos. La regla más importante fue que el agente siempre debía entregar archivos completos y funcionales (app.py, requirements.txt) sin placeholders ni código incompleto. Esto eliminó la fricción habitual de recibir fragmentos de código que luego hay que ensamblar manualmente.

Dificultades al delegar código a la IA

El mayor desafío no fue técnico sino de confianza: resistir el impulso de revisar cada línea de código generado. Al principio quería entender exactamente cómo funcionaba el parser de lenguaje natural, pero el Vibe Coding exige soltar el control de la implementación y enfocarse en el resultado. Otro punto de fricción fue el despliegue: Replit presentó problemas de configuración de puertos y build incorrecto en Node.js que el agente no resolvió de forma autónoma, lo que obligó a cambiar de plataforma a Streamlit Community Cloud, donde el despliegue fue inmediato.

De "escribir código" a "orquestar una visión"

El cambio más profundo fue mental. Antes, desarrollar esta app hubiera significado horas investigando cómo parsear texto en español, qué factores de CO2 usar, cómo estructurar los componentes de Streamlit. En cambio, el proceso consistió en describir el producto como si se lo explicara a un colega: "quiero que el usuario escriba su día en lenguaje natural y obtenga su huella de carbono con gráficos". El agente tomó esa intención y la tradujo en 400 líneas de código funcional con métricas, gráficos de barras, donut chart y historial de sesión. El rol cambió de ejecutor a director: yo definí qué debía sentirse correcto, y la IA se encargó de que funcionara.

Captura:
<img width="2559" height="819" alt="image" src="https://github.com/user-attachments/assets/c7cef2a0-5a29-4828-8e21-10d30165b296" />
