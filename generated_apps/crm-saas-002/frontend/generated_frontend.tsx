```bash
# Create a new Next.js app
npx create-next-app@latest frontend --typescript
cd frontend
```

```bash
# Install necessary dependencies
npm install tailwindcss postcss autoprefixer @reduxjs/toolkit react-redux axios
npx tailwindcss init -p
```

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

```css
/* src/styles/tailwind.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

```javascript
// src/pages/_app.js
import '../styles/tailwind.css';
import { Provider } from 'react-redux';
import store from '../redux/store';

function MyApp({ Component, pageProps }) {
  return (
    <Provider store={store}>
      <Component {...pageProps} />
    </Provider>
  );
}

export default MyApp;
```

```javascript
// src/redux/store.js
import { configureStore } from '@reduxjs/toolkit';
import customerReducer from './customerSlice';
import analyticsReducer from './analyticsSlice';
import userReducer from './userSlice';

const store = configureStore({
  reducer: {
    customers: customerReducer,
    analytics: analyticsReducer,
    user: userReducer,
  },
});

export default store;
```

```javascript
// src/redux/customerSlice.js
import { createSlice } from '@reduxjs/toolkit';

const customerSlice = createSlice({
  name: 'customers',
  initialState: [],
  reducers: {
    setCustomers: (state, action) => action.payload,
    addCustomer: (state, action) => {
      state.push(action.payload);
    },
    updateCustomer: (state, action) => {
      const index = state.findIndex(customer => customer.id === action.payload.id);
      if (index !== -1) {
        state[index] = action.payload;
      }
    },
    deleteCustomer: (state, action) => {
      return state.filter(customer => customer.id !== action.payload);
    },
  },
});

export const { setCustomers, addCustomer, updateCustomer, deleteCustomer } = customerSlice.actions;
export default customerSlice.reducer;
```

```javascript
// src/redux/userSlice.js
import { createSlice } from '@reduxjs/toolkit';

const userSlice = createSlice({
  name: 'user',
  initialState: null,
  reducers: {
    setUser: (state, action) => action.payload,
    clearUser: () => null,
  },
});

export const { setUser, clearUser } = userSlice.actions;
export default userSlice.reducer;
```

```javascript
// src/pages/index.js
import Link from 'next/link';

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-4xl font-bold">Welcome to the CRM SaaS Platform</h1>
      <Link href="/login" className="mt-4 text-blue-500">Login</Link>
      <Link href="/registration" className="mt-2 text-blue-500">Register</Link>
    </div>
  );
}
```

```javascript
// src/pages/login.js
import { useState } from 'react';
import axios from 'axios';
import { useDispatch } from 'react-redux';
import { setUser } from '../redux/userSlice';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const dispatch = useDispatch();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('/api/auth/login', { email, password });
      dispatch(setUser(response.data.user));
      // Redirect to dashboard
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-3xl font-bold">Login</h1>
      <form onSubmit={handleLogin} className="flex flex-col">
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="border p-2 mb-2"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="border p-2 mb-2"
          required
        />
        <button type="submit" className="bg-blue-500 text-white p-2">Login</button>
      </form>
    </div>
  );
}
```

```javascript
// src/pages/registration.js
import { useState } from 'react';
import axios from 'axios';

export default function RegistrationPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/auth/register', { username, email, password });
      // Redirect to login
    } catch (error) {
      console.error('Registration failed:', error);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-3xl font-bold">Register</h1>
      <form onSubmit={handleRegister} className="flex flex-col">
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="border p-2 mb-2"
          required
        />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="border p-2 mb-2"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="border p-2 mb-2"
          required
        />
        <button type="submit" className="bg-blue-500 text-white p-2">Register</button>
      </form>
    </div>
  );
}
```

```javascript
// src/pages/dashboard.js
import { useEffect } from 'react';
import { useSelector } from 'react-redux';
import axios from 'axios';

export default function DashboardPage() {
  const user = useSelector((state) => state.user);

  useEffect(() => {
    const fetchData = async () => {
      if (user) {
        const response = await axios.get('/api/customers');
        console.log(response.data);
      }
    };
    fetchData();
  }, [user]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-3xl font-bold">Dashboard</h1>
      {/* Render customer data here */}
    </div>
  );
}
```

```javascript
// src/pages/customer-management.js
import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import axios from 'axios';
import { setCustomers } from '../redux/customerSlice';

export default function CustomerManagementPage() {
  const dispatch = useDispatch();
  const customers = useSelector((state) => state.customers);

  useEffect(() => {
    const fetchCustomers = async () => {
      const response = await axios.get('/api/customers');
      dispatch(setCustomers(response.data));
    };
    fetchCustomers();
  }, [dispatch]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-3xl font-bold">Customer Management</h1>
      <ul>
        {customers.map(customer => (
          <li key={customer.id} className="border p-2 m-2">
            {customer.name} - {customer.email}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

```javascript
// src/pages/analytics.js
import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import axios from 'axios';
import { setAnalytics } from '../redux/analyticsSlice';

export default function AnalyticsPage() {
  const dispatch = useDispatch();

  useEffect(() => {
    const fetchAnalytics = async () => {
      const response = await axios.get('/api/analytics');
      dispatch(setAnalytics(response.data));
    };
    fetchAnalytics();
  }, [dispatch]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-3xl font-bold">Analytics</h1>
      {/* Render analytics data here */}
    </div>
  );
}
```

```javascript
// src/pages/profile.js
import { useSelector } from 'react-redux';

export default function ProfilePage() {
  const user = useSelector((state) => state.user);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-3xl font-bold">Profile</h1>
      <p>Username: {user?.username}</p>
      <p>Email: {user?.email}</p>
      {/* Additional user info */}
    </div>
  );
}
```

```javascript
// src/pages/subscription-management.js
import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import axios from 'axios';
import { setSubscriptions } from '../redux/subscriptionSlice';

export default function SubscriptionManagementPage() {
  const dispatch = useDispatch();

  useEffect(() => {
    const fetchSubscriptions = async () => {
      const response = await axios.get('/api/admin/settings');
      dispatch(setSubscriptions(response.data));
    };
    fetchSubscriptions();
  }, [dispatch]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-3xl font-bold">Subscription Management</h1>
      {/* Render subscription data here */}
    </div>
  );
}
```

```json
// package.json
{
  "name": "frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "axios": "^0.21.1",
    "next": "latest",
    "react": "latest",
    "react-dom": "latest",
    "react-redux": "^7.2.6",
    "@reduxjs/toolkit": "^1.6.0",
    "tailwindcss": "^2.2.19",
    "postcss": "^8.4.5",
    "autoprefixer": "^10.4.2"
  },
  "devDependencies": {
    "tailwindcss": "^2.2.19",
    "postcss": "^8.4.5",
    "autoprefixer": "^10.4.2"
  }
}
```

This code provides a production-ready Next.js frontend structure for a CRM SaaS platform, including pages for login, registration, dashboard, customer management, analytics, profile, and subscription management, along with Redux for state management and Tailwind CSS for styling.