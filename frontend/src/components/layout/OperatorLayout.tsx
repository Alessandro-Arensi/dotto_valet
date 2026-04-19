import { useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  AppShell,
  Group,
  Title,
  UnstyledButton,
  Text,
  Stack,
  ActionIcon,
  Badge,
  Select,
} from '@mantine/core';
import {
  IconBike,
  IconLogin,
  IconLogout,
  IconLayoutDashboard,
  IconCalendarEvent,
  IconUsers,
} from '@tabler/icons-react';
import { useAuthStore } from '../../stores/authStore';
import { useActiveEventStore } from '../../stores/activeEventStore';
import { eventsApi } from '../../api/client';

const baseNavItems = [
  { path: '/', label: 'Dashboard', icon: IconLayoutDashboard },
  { path: '/checkin', label: 'Check-in', icon: IconLogin },
  { path: '/checkout', label: 'Check-out', icon: IconLogout },
];

const adminNavItems = [
  { path: '/admin/events', label: 'Eventi', icon: IconCalendarEvent },
  { path: '/admin/operators', label: 'Operatori', icon: IconUsers },
];

export default function OperatorLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { operator, logout } = useAuthStore();
  const { eventId, setActive, clear } = useActiveEventStore();

  const { data: events } = useQuery({
    queryKey: ['events', 'active'],
    queryFn: () => eventsApi.list(),
  });

  // Auto-pick first active event on first load, or clear stale selection
  useEffect(() => {
    if (!events) return;
    if (events.length === 0) {
      clear();
      return;
    }
    const stillExists = eventId && events.some((e) => e.id === eventId);
    if (!stillExists) {
      const first = events[0];
      setActive(first.id, first.name, first.slug);
    }
  }, [events, eventId, setActive, clear]);

  const handleLogout = () => {
    logout();
    clear();
    navigate('/login');
  };

  const selectOptions = events?.map((e) => ({ value: e.id, label: e.name })) || [];

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
            {selectOptions.length > 0 && (
              <Select
                placeholder="Nessun evento"
                data={selectOptions}
                value={eventId}
                onChange={(v) => {
                  const e = events?.find((ev) => ev.id === v);
                  if (e) setActive(e.id, e.name, e.slug);
                }}
                leftSection={<IconCalendarEvent size={16} />}
                w={220}
                size="sm"
                allowDeselect={false}
              />
            )}
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
          {[
            ...baseNavItems,
            ...(operator?.is_admin ? adminNavItems : []),
          ].map((item) => {
            const isActive = location.pathname === item.path
              || (item.path !== '/' && location.pathname.startsWith(item.path));
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
