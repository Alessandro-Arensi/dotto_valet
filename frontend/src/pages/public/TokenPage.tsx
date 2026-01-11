import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Container,
  Paper,
  Title,
  Text,
  Stack,
  Center,
  Alert,
  Loader,
  Badge,
  Group,
  Button,
  Image,
  Divider,
} from '@mantine/core';
import {
  IconBike,
  IconMapPin,
  IconCalendar,
  IconClock,
  IconAlertCircle,
  IconCheck,
  IconQrcode,
} from '@tabler/icons-react';
import QRCode from 'qrcode.react';

import { tokenApi } from '../../api/client';

export default function TokenPage() {
  const { code } = useParams<{ code: string }>();

  // Fetch token info
  const { data, isLoading, error } = useQuery({
    queryKey: ['tokenInfo', code],
    queryFn: () => tokenApi.getInfo(code!),
    enabled: !!code,
  });

  if (isLoading) {
    return (
      <Center h="100vh">
        <Loader size="lg" />
      </Center>
    );
  }

  if (error || !data) {
    return (
      <Container size="sm" py="xl">
        <Alert icon={<IconAlertCircle size={16} />} color="red">
          Token non trovato
        </Alert>
      </Container>
    );
  }

  const { token, event, checkin } = data;

  const statusColors: Record<string, string> = {
    reserved: 'blue',
    checked_in: 'green',
    checked_out: 'gray',
    expired: 'red',
    lost: 'red',
  };

  const statusLabels: Record<string, string> = {
    reserved: 'Prenotato',
    checked_in: 'Bici parcheggiata',
    checked_out: 'Ritirata',
    expired: 'Scaduto',
    lost: 'Smarrito',
  };

  return (
    <Container size="sm" py="xl">
      <Center mb="xl">
        <IconBike size={64} color="var(--mantine-color-blue-6)" />
      </Center>

      {/* QR Code */}
      <Paper withBorder p="xl" radius="md" ta="center" mb="xl">
        <Center mb="lg">
          <Paper p="md" bg="white" radius="md" shadow="sm">
            <QRCode
              value={`${window.location.origin}/t/${token.code}`}
              size={200}
              level="M"
            />
          </Paper>
        </Center>

        <Title order={2} mb="xs">
          🎫 {token.code}
        </Title>

        <Badge size="lg" color={statusColors[token.status] || 'gray'} mb="md">
          {statusLabels[token.status] || token.status}
        </Badge>

        <Group gap="xs" justify="center">
          <Badge variant="light" color={token.type === 'digital' ? 'blue' : 'orange'}>
            {token.type === 'digital' ? '📱' : '📵'} {token.type}
          </Badge>
        </Group>
      </Paper>

      {/* Event info */}
      {event && (
        <Paper withBorder p="md" radius="md" mb="md">
          <Text size="sm" c="dimmed" tt="uppercase" fw={600} mb="sm">
            Evento
          </Text>
          <Title order={4} mb="xs">{event.name}</Title>
          {event.location && (
            <Group gap="xs" mb="xs">
              <IconMapPin size={16} />
              <Text size="sm">{event.location}</Text>
            </Group>
          )}
          <Group gap="xs">
            <IconCalendar size={16} />
            <Text size="sm">
              {new Date(event.date).toLocaleDateString('it-IT', {
                weekday: 'long',
                day: 'numeric',
                month: 'long',
              })}
            </Text>
          </Group>
        </Paper>
      )}

      {/* Checkin info */}
      {checkin && (
        <Paper withBorder p="md" radius="md" mb="md">
          <Text size="sm" c="dimmed" tt="uppercase" fw={600} mb="sm">
            📍 Posizione Bici
          </Text>
          <Title order={3} mb="xs">{checkin.position}</Title>
          <Group gap="xs">
            <IconClock size={16} />
            <Text size="sm">
              Check-in: {new Date(checkin.checked_in_at).toLocaleString('it-IT')}
            </Text>
          </Group>
          
          {checkin.photo_url && (
            <>
              <Divider my="md" />
              <Text size="sm" fw={500} mb="sm">Foto bici</Text>
              <Image
                src={checkin.photo_url}
                alt="Foto bici"
                radius="md"
                mah={200}
                fit="contain"
              />
            </>
          )}
        </Paper>
      )}

      {/* Instructions based on status */}
      {token.status === 'reserved' && (
        <Alert color="blue" icon={<IconBike size={16} />}>
          Presenta questo QR all'ingresso insieme alla tua bici!
        </Alert>
      )}

      {token.status === 'checked_in' && (
        <Alert color="green" icon={<IconCheck size={16} />}>
          La tua bici è al sicuro! Mostra questo QR per ritirarla.
        </Alert>
      )}

      {token.status === 'checked_out' && (
        <Alert color="gray">
          Bici già ritirata. Grazie per aver usato Dottò!
        </Alert>
      )}

      {/* Actions */}
      <Stack mt="xl">
        <Button
          variant="light"
          leftSection={<IconQrcode size={18} />}
          onClick={() => {/* TODO: Add to wallet */}}
        >
          📲 Aggiungi a Google Wallet
        </Button>
      </Stack>

      <Text c="dimmed" size="xs" ta="center" mt="xl">
        Dottò - by Scintilla Cicloprogetti
      </Text>
    </Container>
  );
}


