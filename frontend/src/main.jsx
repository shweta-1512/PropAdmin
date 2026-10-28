import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  LayoutDashboard, Users, Building2, ClipboardList, MessageSquareWarning,
  ShieldCheck, Settings, LogOut, Bell, Search, Plus, Check, X, Menu,
  FileText, Clock3, AlertTriangle, CheckCircle2, ArrowRight, LockKeyhole
} from 'lucide-react';
import './style.css';

const API = 'http://127.0.0.1:8000/api';
const taskCategories = [
  'Admin, Office',
  'Security and Safety',
  'Housekeeping and Hygiene',
  'Repair and Maintenance',
  'Other - General'
];
const navigation = [
  ['Dashboard', 'dashboard', LayoutDashboard],
  ['Pending Approvals', 'approvals', Bell],
  ['Users', 'users', Users],
  ['Projects', 'projects', Building2],
  ['Tasks', 'tasks', ClipboardList],
  ['Complaints', 'complaints', MessageSquareWarning],
  ['Compliance', 'compliances', ShieldCheck],
  ['Roles', 'roles', Settings],
  ['Audit Log', 'audit', FileText]
];

function App() {
  const [user, setUser] = useState(null);
  const [page, setPage] = useState('dashboard');
  const [email, setEmail] = useState('admin@propadmin.in');
  const [password, setPassword] = useState('Admin@123');
  const [data, setData] = useState([]);
  const [dashboardData, setDashboardData] = useState({ users: [], projects: [], tasks: [], complaints: [], compliances: [] });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const isSuper = user?.role === 'Super Admin' || user?.role === 'SuperAdmin';

  
  async function req(path, options = {}) {
    const token = localStorage.getItem('propadmin_token');

    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {})
    };

    const response = await fetch(API + path, {
      ...options,
      headers
    });

    let result;
    try {
      result = await response.json();
    } catch {
      result = {};
    }

    if (!response.ok) {
      throw new Error(
        result.detail || result.message || `Request failed (${response.status})`
      );
    }

    return result;
  }

  async function login(event) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const loggedInUser = await req('/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      localStorage.setItem('propadmin_token', loggedInUser.access_token);
      setUser(loggedInUser);
      setPage('dashboard');
    } catch (err) {
      setError(err.message || 'Unable to sign in. Check your details and try again.');
    } finally {
      setLoading(false);
    }
  }

  async function load() {
    if (!user) return;
    setLoading(true);
    setError('');
    const endpoints = {
      approvals: '/users/pending', users: '/users', projects: '/projects',
      tasks: '/tasks', complaints: '/complaints', compliances: '/compliances',
      roles: '/roles', audit: '/audit'
    };
    try {
      if (page === 'dashboard') {
        const entries = await Promise.all(Object.entries({
          users: '/users', projects: '/projects', tasks: '/tasks',
          complaints: '/complaints', compliances: '/compliances'
        }).map(async ([key, endpoint]) => {
          try { return [key, await req(endpoint)]; } catch { return [key, []]; }
        }));
        setDashboardData(Object.fromEntries(entries));
        setData([]);
      } else {
        const endpoint = endpoints[page];
        setData(endpoint ? await req(endpoint) : []);
      }
    } catch (err) {
      setError(err.message || 'Could not load records.');
      setData([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { if (user) load(); }, [user, page]);

  async function action(path, successMessage) {
    setError('');
    setNotice('');
    try {
      await req(path, { method: 'POST', body: '{}' });
      setNotice(successMessage);
      await load();
    } catch (err) {
      setError(err.message || 'Action failed.');
    }
  }

  async function submitForm(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    const endpoints = {
      users: '/users', projects: '/projects', tasks: '/tasks',
      complaints: '/complaints', compliances: '/compliances', roles: '/roles'
    };
    if (page === 'users' && !payload.password) payload.password = 'ChangeMe123!';
    try {
      await req(endpoints[page], { method: 'POST', body: JSON.stringify(payload) });
      setShowForm(false);
      setNotice(`${page[0].toUpperCase() + page.slice(1)} record created successfully.`);
      await load();
    } catch (err) {
      setError(err.message || 'Could not save this record.');
    }
  }

  const title = page === 'approvals' ? 'Pending Approvals' : page[0].toUpperCase() + page.slice(1);
  const pendingCount = page === 'approvals'
    ? data.filter(item => item.status === 'Pending').length
    : (dashboardData.users || []).filter(item => item.status === 'Pending').length;
  const cards = [
    { label: 'Open tasks', value: (dashboardData.tasks || []).filter(x => !['Completed', 'Closed'].includes(x.status)).length, note: 'Across your projects', icon: ClipboardList, page: 'tasks', color: 'blue' },
    { label: 'Pending approvals', value: pendingCount, note: 'Users waiting for review', icon: Clock3, page: 'approvals', color: 'amber' },
    { label: 'Compliance alerts', value: (dashboardData.compliances || []).length, note: 'Records to review', icon: AlertTriangle, page: 'compliances', color: 'red' },
    { label: 'Projects', value: (dashboardData.projects || []).length, note: 'Projects in the workspace', icon: CheckCircle2, page: 'projects', color: 'green' }
  ];
  const filteredData = data.filter(row => Object.values(row).some(value => String(value ?? '').toLowerCase().includes(searchTerm.toLowerCase())));

  if (!user) {
    return (
      <div className="login-page">
        <section className="login-hero">
          <div className="login-brand">
  <img
    src="/PropAdmin-logo.png"
    alt="Logo"
    className="propadmin-symbol login-symbol"
  />
</div><div className="hero-copy">
            <p className="eyebrow light">PROPERTY OPERATIONS PLATFORM</p>
            <h1>One place to manage <span>every property.</span></h1>
            <p>A working space for your properties, projects, tasks and teams — all in one secure portal.</p>
          </div>
          <div className="hero-foot"><LockKeyhole size={16} /> Secure property operations platform</div>
          <div className="hero-shape shape-one" /><div className="hero-shape shape-two" />
        </section>
        <section className="login-side">
          <div className="login-form-wrap">
            <p className="eyebrow">WELCOME BACK</p>
            <h2>Sign in to PropAdmin</h2>
            <p className="muted login-subtitle">Use your account details to access your workspace.</p>
            <form onSubmit={login} className="login-form">
              <label htmlFor="email">Email address</label>
              <input id="email" value={email} onChange={e => setEmail(e.target.value)} type="email" autoComplete="username" required />
              <label htmlFor="password">Password</label>
              <input id="password" value={password} onChange={e => setPassword(e.target.value)} type="password" autoComplete="current-password" required />
              {error && <div className="error">{error}</div>}
              <button className="primary login-submit" disabled={loading}>{loading ? 'Signing in…' : 'Sign in'} <ArrowRight size={18} /></button>
            </form>
            <div className="demo-box"><strong>Demo access</strong><p>Super Admin: <b>admin@propadmin.in</b></p><p>Manager: <b>manager@propadmin.in</b></p><p>Client: <b>client@propadmin.in</b></p><small>Use the passwords configured for your local demo accounts.</small></div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {mobile && <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMobile(false)} />}
      <aside className={`sidebar ${mobile ? 'sidebar-open' : ''}`}>
        <div className="brand">
  <img
    src="/PropAdmin-logo.png"
    alt="Logo"
    className="propadmin-symbol sidebar-symbol"
  />
  <button
    className="close-nav"
    onClick={() => setMobile(false)}
    aria-label="Close menu"
  >
    <X size={19} />
  </button>
</div><div className="nav-label">WORKSPACE</div>
        <nav>{navigation.filter(([label]) => isSuper || !['Pending Approvals', 'Roles', 'Audit Log', 'Users'].includes(label)).map(([label, key, Icon]) => (
          <button key={key} className={`nav-item ${page === key ? 'active' : ''}`} onClick={() => { setPage(key); setShowForm(false); setMobile(false); }}>
            <Icon size={19} /><span>{label}</span>{key === 'approvals' && isSuper && pendingCount > 0 && <i>{pendingCount}</i>}
          </button>
        ))}</nav>
        <div className="sidebar-bottom"><div className="user-mini"><div className="avatar">{(user.name || user.email || 'U')[0].toUpperCase()}</div><div className="user-info"><b>{user.name || 'User'}</b><small>{user.role || 'Member'}</small></div></div><button className="nav-item signout" onClick={() => {
localStorage.removeItem('propadmin_token');
setUser(null);
setData([]);
setError('');
setNotice('');
setPage('dashboard');
}}
><LogOut size={18} /><span>Sign out</span></button></div>
      </aside>
      <main className="main-area">
        <header className="topbar"><button className="hamburger" onClick={() => setMobile(true)} aria-label="Open menu"><Menu /></button><div className="breadcrumb">Workspace <span>/</span> {title}</div><div className="top-actions"><label className="search-box"><Search size={17} /><input id="global-search" name="global-search" aria-label="Search records" placeholder="Search records" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} /></label><button className="top-bell" aria-label="Pending approvals" onClick={() => setPage('approvals')}><Bell size={19} />{pendingCount > 0 && <i />}</button><div className="top-user"><span className="status-dot" />{user.role || 'Member'}</div></div></header>
        <section className="page-content">
          <div className="welcome-row"><div><p className="eyebrow">{page === 'dashboard' ? 'PROPERTY OPERATIONS' : (user.role || 'USER').toUpperCase() + ' WORKSPACE'}</p><h1>{page === 'dashboard' ? `Good to see you, ${(user.name || 'there').split(' ')[0]}` : title}</h1><p className="muted">{page === 'dashboard' ? 'Here is a quick view of what needs attention today.' : page === 'approvals' ? 'Review new accounts before they can sign in.' : `Manage and review your ${title.toLowerCase()}.`}</p></div>{['users', 'projects', 'tasks', 'complaints', 'compliances', 'roles'].includes(page) && isSuper && <button className="primary create-button" onClick={() => setShowForm(!showForm)}><Plus size={17} /> Create {page === 'users' ? 'User' : page === 'projects' ? 'Project' : page === 'tasks' ? 'Task' : page === 'complaints' ? 'Complaint' : page === 'compliances' ? 'Compliance' : 'Role'}</button>}</div>
          {error && <div className="error banner">{error}</div>}{notice && <div className="success banner">{notice}</div>}
          {page === 'dashboard' ? <>
            <div className="stat-grid">{cards.map(({ label, value, note, icon: Icon, page: target, color }) => <button className="stat-card" key={label} onClick={() => setPage(target)}><span className={`stat-icon ${color}`}><Icon size={21} /></span><span className="stat-label">{label}</span><strong className="stat-value">{value}</strong><small>{note}</small></button>)}</div>
            <div className="dashboard-columns"><div className="panel attention-panel"><div className="panel-head"><div><h3>Items requiring attention</h3><p className="muted">Latest workspace records</p></div><span className="today-pill">Today</span></div>
              {((dashboardData.tasks || []).filter(x => !['Completed', 'Closed'].includes(x.status)).slice(0, 4)).length ? (dashboardData.tasks || []).filter(x => !['Completed', 'Closed'].includes(x.status)).slice(0, 4).map((task, index) => <div className="attention-row" key={task.id ?? index}><span className="row-dot" /><div className="attention-copy"><b>{task.title || 'Task'}</b><small>{task.assigned_to || task.category || 'Unassigned'}</small></div><span className="mini-badge">{task.status || 'Pending'}</span></div>) : <div className="empty compact"><b>No open tasks</b><p className="muted">New tasks will appear here.</p></div>}
            </div><div className="panel health-panel"><div className="panel-head"><div><h3>Workspace overview</h3><p className="muted">Current record counts</p></div></div><div className="overview-list"><div><span><Users size={17} /> Users</span><b>{(dashboardData.users || []).length}</b></div><div><span><Building2 size={17} /> Projects</span><b>{(dashboardData.projects || []).length}</b></div><div><span><ClipboardList size={17} /> Tasks</span><b>{(dashboardData.tasks || []).length}</b></div><div><span><ShieldCheck size={17} /> Compliance records</span><b>{(dashboardData.compliances || []).length}</b></div></div><button className="secondary overview-link" onClick={() => setPage('projects')}>View projects <ArrowRight size={15} /></button></div></div>
            <div className="panel quick-panel"><div className="panel-head"><div><h3>Quick actions</h3><p className="muted">Jump straight into your workspace</p></div></div><div className="quick-grid">{[['Review pending users', 'approvals'], ['Manage projects', 'projects'], ['Track tasks', 'tasks'], ['Review complaints', 'complaints']].map(([label, target]) => <button key={target} onClick={() => setPage(target)}>{label}<ArrowRight size={17} /></button>)}</div></div>
          </> : <div className="panel records-panel"><div className="panel-head"><div><h3>{title}</h3><p className="muted">{page === 'approvals' ? 'Approve or reject users who are waiting for access.' : 'Records stored in your PropAdmin database.'}</p></div><button className="secondary" onClick={load}>Refresh</button></div>
            {showForm && <form className="create-form" onSubmit={submitForm}><h3>Create {page === 'users' ? 'User' : page === 'projects' ? 'Project' : page === 'tasks' ? 'Task' : page === 'complaints' ? 'Complaint' : page === 'compliances' ? 'Compliance' : 'Role'}</h3>
              {page === 'users' && <><input name="name" placeholder="Full name" required /><input name="email" type="email" placeholder="Email address" required /><input name="password" type="password" placeholder="Temporary password" required /><input name="phone" placeholder="Phone number (optional)" /><select name="role" defaultValue="Manager">{['Admin', 'Manager', 'Customer', 'Vendor', 'Accountant', 'Technical Staff', 'Help Desk', 'Back-End'].map(role => <option key={role}>{role}</option>)}</select></>}
              {page === 'projects' && <><input name="name" placeholder="Project / Society name" required /><input name="organisation" placeholder="Organisation" /><input name="address" placeholder="Address" /></>}
              {page === 'tasks' && <><input name="title" placeholder="Task title" required /><label className="field-label">Task category<select name="category" defaultValue={taskCategories[0]}>{taskCategories.map(category => <option key={category}>{category}</option>)}</select></label><label className="field-label">Related to Asset (Optional)<select name="related_asset" defaultValue=""><option value="">No asset selected</option><option>Lift</option><option>Generator</option><option>Other Available Asset</option></select></label><input name="assigned_to" placeholder="Assigned staff / email" /><label className="field-label">Expected completion date<input name="expected_date" type="date" /></label><label className="field-label">Priority<select name="priority" defaultValue="Medium"><option>Low</option><option>Medium</option><option>High</option><option>Urgent</option></select></label><textarea name="description" placeholder="Task description" /></>}
              {page === 'complaints' && <><input name="title" placeholder="Complaint title" required /><input name="reported_by" placeholder="Reported by" /><input name="assigned_to" placeholder="Assigned staff" /><label className="field-label">Expected completion date<input name="expected_date" type="date" /></label><label className="field-label">Priority<select name="priority" defaultValue="Medium"><option>Low</option><option>Medium</option><option>High</option><option>Urgent</option></select></label><textarea name="description" placeholder="Description" /></>}
              {page === 'compliances' && <><input name="name" placeholder="Compliance name" required /><input name="responsible_person" placeholder="Responsible person" /><label className="field-label">Due date<input name="due_date" type="date" /></label><input name="evidence" placeholder="Evidence / document reference" /></>}
              {page === 'roles' && <><input name="name" placeholder="Role name" required /><input name="description" placeholder="Role description" /></>}
              <div className="form-actions"><button className="primary" disabled={loading}>Save</button><button type="button" className="secondary" onClick={() => setShowForm(false)}>Cancel</button></div>
            </form>}
            {loading ? <div className="loading-state">Loading records…</div> : filteredData.length === 0 ? <div className="empty"><span className="empty-icon"><FileText size={22} /></span><b>{page === 'approvals' ? 'No pending approvals' : 'No records found'}</b><p className="muted">{page === 'approvals' ? 'Newly registered users will appear here.' : 'Create a record or refresh to check again.'}</p></div> : <div className="table-wrap"><table><thead><tr>{Object.keys(filteredData[0]).filter(key => key !== 'password_hash').map(key => <th key={key}>{key.replaceAll('_', ' ')}</th>)}{['approvals', 'tasks', 'complaints', 'compliances'].includes(page) && (
  <th>Actions</th>
)}</tr></thead><tbody>{filteredData.filter(row => page !== 'approvals' || row.status === 'Pending').map((row, index) => <tr key={row.id ?? index}>{Object.entries(row).filter(([key]) => key !== 'password_hash').map(([key, value]) => <td key={key}>{key === 'status' ? <span className={`badge ${String(value).toLowerCase()}`}>{value}</span> : String(value ?? '—')}</td>)}{['approvals', 'tasks', 'complaints', 'compliances'].includes(page) && (
  <td>
    {(
      page === 'approvals'
        ? row.status === 'Pending'
        : ['Pending', 'Open'].includes(row.status)
    ) ? (
      <div className="actions">
        <button
          className="approve"
          title="Approve"
          onClick={() => {
            const base = {
              approvals: '/users',
              tasks: '/tasks',
              complaints: '/complaints',
              compliances: '/compliances'
            }[page];

            action(
              `${base}/${row.id}/approve`,
              `${page} record approved successfully.`
            );
          }}
        >
          <Check size={16} />
        </button>

        <button
          className="reject"
          title="Reject"
          onClick={() => {
            const base = {
              approvals: '/users',
              tasks: '/tasks',
              complaints: '/complaints',
              compliances: '/compliances'
            }[page];

            action(
              `${base}/${row.id}/reject`,
              `${page} record rejected.`
            );
          }}
        >
          <X size={16} />
        </button>
      </div>
    ) : (
      <span>—</span>
    )}
  </td>
)}</tr>)}</tbody></table></div>}
          </div>}
          <footer><span>PropAdmin · Property operations</span><span>Secure workspace</span></footer>
        </section>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);









