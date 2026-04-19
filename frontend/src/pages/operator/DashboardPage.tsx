import { useQuery } from '@tanstack/react-query';
import {
  Title,
  Text,
  Paper,
  Group,
  Stack,
  SimpleGrid,
  RingProgress,
  Badge,
  Table,
  Alert,
  Button,
} from '@mantine/core';
import {
  IconBike,
  IconParking,
  IconClock,
  IconAlertCircle,
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';

import { eventsApi, checkinApi } from '../../api/client';
import { useActiveEventStore } from '../../stores/activeEventStore';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { eventId: activeEventId, eventName, eventSlug } = useActiveEventStore();

  const { data: stats } = useQuery({
    queryKey: ['eventStats', activeEventId],
    queryFn: () => eventsApi.getStats(activeEventId!),
    enabled: !!activeEventId,
    refetchInterval: 30000,
  });

  const { data: checkins } = useQuery({
    queryKey: ['checkins', activeEventId],
    queryFn: () => checkinApi.list(activeEventId!, 'active'),
    enabled: !!activeEventId,
    refetchInterval: 30000,
  });

  if (!activeEventId) {
    return (
      <Alert icon={<IconAlertCircle size={16} />} title="Nessun evento attivo" color="yellow">
        Non ci sono eventi attivi al momento. Creane uno da <strong>Eventi</strong>.
      </Alert>
    );
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <div>
          <Title order={2}>{eventName}</Title>
          <Text c="dimmed">slug: {eventSlug}</Text>
        </div>
        <Group>
          <Button onClick={() => navigate('/checkin')} leftSection={<IconBike size={18} />}>
            Check-in
          </Button>
          <Button variant="light" onClick={() => navigate('/checkout')}>
            Check-out
          </Button>
        </Group>
      </Group>

      {/* Stats cards */}
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <StatsCard
          title="Bici Parcheggiate"
          value={stats?.checked_in ?? 0}
          total={stats?.total_capacity ?? 0}
          icon={IconBike}
          color="blue"
        />
        <StatsCard
          title="Posti Disponibili"
          value={stats?.available ?? 0}
          total={stats?.total_capacity ?? 0}
          icon={IconParking}
          color="green"
        />
        <StatsCard
          title="Prenotazioni"
          value={stats?.reserved ?? 0}
          total={stats?.total_capacity ?? 0}
          icon={IconClock}
          color="orange"
        />
        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Occupazione
              </Text>
              <Text size="xl" fw={700}>
                {stats?.occupancy_percent?.toFixed(0) ?? 0}%
              </Text>
            </div>
            <RingProgress
              size={80}
              roundCaps
              thickness={8}
              sections={[
                {
                  value: stats?.occupancy_percent ?? 0,
                  color: (stats?.occupancy_percent ?? 0) > 80 ? 'orange' : 'blue',
                },
              ]}
            />
          </Group>
          {stats?.suggest_fast_mode && (
            <Badge color="orange" mt="sm">
              ⚡ Modalità veloce consigliata
            </Badge>
          )}
        </Paper>
      </SimpleGrid>

      {/* Recent checkins */}
      <Paper withBorder p="md" radius="md">
        <Title order={4} mb="md">
          Bici Parcheggiate ({checkins?.length ?? 0})
        </Title>
        {checkins && checkins.length > 0 ? (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Token</Table.Th>
                <Table.Th>Posizione</Table.Th>
                <Table.Th>Orario</Table.Th>
                <Table.Th>Tipo</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {checkins.slice(0, 10).map((checkin) => (
                <Table.Tr key={checkin.id}>
                  <Table.Td>
                    <Text fw={500}>{checkin.token_code}</Text>
                  </Table.Td>
                  <Table.Td>
                    {checkin.rack_label || `Rast. ${checkin.rack_number}`}, Slot{' '}
                    {checkin.slot_number}
                  </Table.Td>
                  <Table.Td>
                    {new Date(checkin.checked_in_at).toLocaleTimeString('it-IT', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      color={checkin.token_type === 'digital' ? 'blue' : 'orange'}
                      variant="light"
                    >
                      {checkin.token_type === 'digital' ? '📱' : '📵'} {checkin.token_type}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        ) : (
          <Text c="dimmed" ta="center" py="xl">
            Nessuna bici parcheggiata
          </Text>
        )}
      </Paper>
    </Stack>
  );
}

function StatsCard({
  title,
  value,
  total,
  icon: Icon,
}: {
  title: string;
  value: number;
  total: number;
  icon: React.ComponentType<{ size: number }>;
  color?: string;
}) {
  return (
    <Paper withBorder p="md" radius="md">
      <Group justify="space-between">
        <div>
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
            {title}
          </Text>
          <Text size="xl" fw={700}>
            {value}
            <Text span size="sm" c="dimmed" fw={400}>
              {' '}
              / {total}
            </Text>
          </Text>
        </div>
        <Icon size={32} />
      </Group>
    </Paper>
  );
}


