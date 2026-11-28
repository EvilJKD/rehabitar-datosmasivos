import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./pages/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'analitica',
    loadComponent: () =>
      import('./pages/analitica/analitica.component').then((m) => m.AnaliticaComponent),
  },
  {
    path: 'municipio/:codigo_ine',
    loadComponent: () =>
      import('./pages/municipio-detail/municipio-detail.component').then(
        (m) => m.MunicipioDetailComponent,
      ),
  },
  {
    path: 'convocatorias',
    loadComponent: () =>
      import('./pages/convocatorias/convocatorias.component').then((m) => m.ConvocatoriasComponent),
  },
  { path: '**', redirectTo: '/dashboard' },
];
