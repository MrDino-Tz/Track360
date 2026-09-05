import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="text-center py-10">
      <h1 className="display-4 mb-3">404</h1>
      <p className="text-secondary mb-4">This page doesn't exist (or never did).</p>
      <Link to="/" className="btn btn-primary"><i className="ti ti-home me-1"></i> Back to dashboard</Link>
    </div>
  );
}