import { describe, expect, it } from 'vitest';
import { routes } from '../../router';

describe('router', () => {
  it('defines the eight workflow routes', () => {
    const paths = routes.map((route) => route.path);
    expect(paths).toContain('/');
    expect(paths).toEqual(expect.arrayContaining(['/seed', '/config', '/models', '/run', '/review', '/report', '/history', '/settings']));
  });

  it('maps each workflow route to a component', () => {
    const workflowRoutes = routes.filter((route) => ['/seed', '/config', '/models', '/run', '/review', '/report', '/history', '/settings'].includes(route.path));
    expect(workflowRoutes).toHaveLength(8);
    expect(workflowRoutes.every((route) => Boolean('component' in route && route.component))).toBe(true);
  });
});
