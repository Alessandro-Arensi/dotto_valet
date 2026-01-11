import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  AppShell,
  Group,
  Title,
  UnstyledButton,
  Text,
  Stack,
  ActionIcon,
  Badge,
} from '@mantine/core';
import {
  IconBike,
  IconLogin,
  IconLogout,
  IconLayoutDashboard,
  IconQrcode,
} from '@tabler/icons-react';
import { useAuthStore } from '../../stores/authStore';

const navItems = [
  { path: '/', label: 'Dashboard', icon: IconLayoutDashboard },
  { path: '/checkin', label: 'Check-in', icon: IconLogin },
  { path: '/checkout', label: 'Check-out', icon: IconLogout },
];

export default function OperatorLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { operator, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 80, breakpoint: 'sm', collapsed: { mobile: false } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <IconBike size={32} color="var(--mantine-color-blue-6)" />
            <Title order={3}>Dottò</Title>
          </Group>
          <Group>
            {operator && (
              <Badge variant="light" size="lg">
                {operator.name}
              </Badge>
            )}
            <ActionIcon
              variant="subtle"
              size="lg"
              onClick={handleLogout}
              title="Logout"
            >
              <IconLogout size={20} />
            </ActionIcon>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        <Stack gap="xs" align="center">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <UnstyledButton
                key={item.path}
                onClick={() => navigate(item.path)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  padding: '12px 8px',
                  borderRadius: 'var(--mantine-radius-md)',
                  backgroundColor: isActive
                    ? 'var(--mantine-color-blue-light)'
                    : 'transparent',
                  width: '100%',
                }}
              >
                <Icon
                  size={24}
                  color={
                    isActive
                      ? 'var(--mantine-color-blue-6)'
                      : 'var(--mantine-color-gray-6)'
                  }
                />
                <Text
                  size="xs"
                  mt={4}
                  c={isActive ? 'blue' : 'gray'}
                  fw={isActive ? 600 : 400}
                >
                  {item.label}
                </Text>
              </UnstyledButton>
            );
          })}
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}


