import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
//导入路由,redux
import { BrowserRouter } from 'react-router-dom'
import { Provider } from 'react-redux'
//导入Slice
import store from './utils/store.js'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
    <Provider store={store}>
      <App />
    </Provider>
    </BrowserRouter>

  </StrictMode>
)
