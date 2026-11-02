import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';

import './styles/variables.css';
import './styles/base.css';
import './styles/forms.css';
import './styles/tables.css';
import './styles/modals.css';
import './styles/components.css';
import './styles/live.css';
import './styles/file-browser.css';
import './styles/animations.css';


ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
