import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import './index.css'

// StrictMode disabled: voice streaming playback triggers MSE SourceBuffer
// residual reuse under dev double-mount. Re-enable once player lifecycle
// is fully idempotent.
createRoot(document.getElementById('root')!).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>,
)
