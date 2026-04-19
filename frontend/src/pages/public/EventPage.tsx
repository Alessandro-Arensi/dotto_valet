import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Container,
  Paper,
  Title,
  Text,
  TextInput,
  Button,
  Stack,
  Center,
  Alert,
  Progress,
  Group,
  Checkbox,
  Loader,
  Badge,
  Tabs,
  Divider,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import QRCode from 'qrcode.react';
import {
  IconBike,
  IconMapPin,
  IconCalendar,
  IconClock,
  IconMail,
  IconAlertCircle,
  IconCheck,
  IconWalk,
  IconCamera,
  IconUser,
} from '@tabler/icons-react';

import {
  eventsApi,
  ReservationRequest,
  ReservationResponse,
  WalkinRequest,
  WalkinResponse,
} from '../../api/client';

type Mode = 'reserve' | 'walkin';

interface Props {
  defaultTab?: Mode;
}

export default function EventPage({ defaultTab = 'reserve' }: Props) {
  const { slug } = useParams<{ slug: string }>();
  const [activeTab, setActiveTab] = useState<Mode>(defaultTab);
  const [reservationResult, setReservationResult] =
    useState<ReservationResponse | null>(null);
  const [walkinResult, setWalkinResult] = useState<WalkinResponse | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['eventAvailability', slug],
    queryFn: () => eventsApi.getAvailability(slug!),
    enabled: !!slug,
  });

  const reserveForm = useForm({
    initialValues: {
      first_name: '',
      last_name: '',
      email: '',
      newsletter: false,
    },
    validate: {
      first_name: (v) => (v.trim().length >= 1 ? null : 'Nome richiesto'),
      last_name: (v) => (v.trim().length >= 1 ? null : 'Cognome richiesto'),
    },
  });

  const walkinForm = useForm({
    initialValues: { first_name: '', last_name: '' },
    validate: {
      first_name: (v) => (v.trim().length >= 1 ? null : 'Nome richiesto'),
      last_name: (v) => (v.trim().length >= 1 ? null : 'Cognome richiesto'),
    },
  });

  const reserveMutation = useMutation({
    mutationFn: (payload: ReservationRequest) =>
      eventsApi.reserve(slug!, payload),
    onSuccess: (response) => setReservationResult(response),
    onError: (err: Error) =>
      notifications.show({
        title: 'Prenotazione non riuscita',
        message: err.message,
        color: 'red',
        icon: <IconAlertCircle size={16} />,
      }),
  });

  const walkinMutation = useMutation({
    mutationFn: (payload: WalkinRequest) => eventsApi.walkin(slug!, payload),
    onSuccess: (response) => setWalkinResult(response),
    onError: (err: Error) =>
      notifications.show({
        title: 'Check-in non riuscito',
        message: err.message,
        color: 'red',
        icon: <IconAlertCircle size={16} />,
      }),
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
          Evento non trovato
        </Alert>
      </Container>
    );
  }

  const { event, availability, can_reserve, message } = data;

  // =========== Reservation success screen ===========
  if (reservationResult) {
    const qrTarget = `${window.location.origin}/t/${reservationResult.token.code}`;
    return (
      <Container size="sm" py="xl">
        <Center mb="xl">
          <IconCheck size={64} color="var(--mantine-color-green-6)" />
        </Center>

        <Title ta="center" order={2} c="green">
          ✅ Prenotato!
        </Title>
        <Text ta="center" c="dimmed" mt="xs">
          {reservationResult.reservation.customer_name}
        </Text>

        <Paper withBorder p="xl" mt="xl" radius="md" ta="center">
          <Center mb="lg">
            <Paper p="md" bg="white" radius="md" shadow="sm">
              <QRCode value={qrTarget} size={220} level="M" />
            </Paper>
          </Center>

          <Text size="xl" fw={700} mb="xs">
            🎫 {reservationResult.token.code}
          </Text>
          <Text c="dimmed" mb="lg">
            {event.name}
          </Text>

          <Alert
            color="yellow"
            variant="light"
            icon={<IconCamera size={18} />}
            mb="md"
          >
            <Text fw={600}>Fai uno screenshot di questa pagina</Text>
            <Text size="sm">
              Mostra il QR all'ingresso il giorno dell'evento per il check-in.
            </Text>
          </Alert>

          <Button
            component={Link}
            to={`/t/${reservationResult.token.code}`}
            fullWidth
            variant="light"
          >
            Apri pagina ticket
          </Button>
        </Paper>

        <Text ta="center" c="dimmed" mt="lg" size="sm">
          Servizio SMS in arrivo. Per ora conserva lo screenshot.
        </Text>
      </Container>
    );
  }

  // =========== Walk-in success screen ===========
  if (walkinResult) {
    const qrTarget = `${window.location.origin}/t/${walkinResult.token.code}`;
    const rackLabel =
      walkinResult.position.rack_label ||
      `Rastrelliera ${walkinResult.position.rack_number}`;
    return (
      <Container size="sm" py="xl">
        <Center mb="xl">
          <IconCheck size={64} color="var(--mantine-color-green-6)" />
        </Center>

        <Title ta="center" order={2} c="green">
          ✅ Check-in effettuato!
        </Title>
        <Text ta="center" c="dimmed" mt="xs">
          {walkinResult.customer_name}
        </Text>

        <Paper withBorder p="xl" mt="xl" radius="md" ta="center">
          <Center mb="lg">
            <Paper p="md" bg="white" radius="md" shadow="sm">
              <QRCode value={qrTarget} size={220} level="M" />
            </Paper>
          </Center>

          <Text size="xl" fw={700} mb="xs">
            🎫 {walkinResult.token.code}
          </Text>

          <Paper p="md" withBorder radius="md" mb="md" bg="blue.0">
            <Group justify="center" gap="xs" mb="xs">
              <IconMapPin size={20} />
              <Text fw={700} size="lg">
                {rackLabel}, Slot {walkinResult.position.slot_number}
              </Text>
            </Group>
            <Text size="sm" c="dimmed">
              Posteggia la bici in questa posizione
            </Text>
          </Paper>

          <Alert
            color="yellow"
            variant="light"
            icon={<IconCamera size={18} />}
          >
            <Text fw={600}>Fai uno screenshot ora</Text>
            <Text size="sm">
              Serve al ritiro. Se lo perdi, chiedi all'operatore di cercarti
              per nome e cognome.
            </Text>
          </Alert>
        </Paper>

        <Text ta="center" c="dimmed" mt="lg" size="sm">
          Mostra il QR all'operatore quando ritiri la bici.
        </Text>
      </Container>
    );
  }

  const busy = availability.percent >= 80;

  return (
    <Container size="sm" py="xl">
      <Center mb="xl">
        <IconBike size={64} color="var(--mantine-color-blue-6)" />
      </Center>

      <Title ta="center" order={2}>
        {event.name}
      </Title>

      <Stack gap="xs" mt="md" mb="xl">
        {event.location && (
          <Group justify="center" gap="xs">
            <IconMapPin size={16} />
            <Text size="sm" c="dimmed">
              {event.location}
            </Text>
          </Group>
        )}
        <Group justify="center" gap="xs">
          <IconCalendar size={16} />
          <Text size="sm" c="dimmed">
            {new Date(event.start_date).toLocaleDateString('it-IT', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
          </Text>
        </Group>
        {event.checkin_opens_at && (
          <Group justify="center" gap="xs">
            <IconClock size={16} />
            <Text size="sm" c="dimmed">
              Check-in dalle{' '}
              {new Date(event.checkin_opens_at).toLocaleTimeString('it-IT', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Text>
          </Group>
        )}
      </Stack>

      <Paper withBorder p="md" radius="md" mb="xl">
        <Text size="sm" c="dimmed" tt="uppercase" fw={600} mb="xs">
          🅿️ Posti Disponibili
        </Text>
        <Progress
          value={availability.percent}
          size="xl"
          color={busy ? 'orange' : 'blue'}
          mb="xs"
        />
        <Group justify="space-between">
          <Text size="sm" fw={500}>
            {availability.available} / {availability.total} posti
          </Text>
          <Badge color={busy ? 'orange' : 'blue'}>
            {availability.percent.toFixed(0)}%
          </Badge>
        </Group>
      </Paper>

      {message && (
        <Alert color={can_reserve ? 'blue' : 'orange'} mb="xl">
          {message}
        </Alert>
      )}

      {!can_reserve ? (
        <Alert color="red" icon={<IconAlertCircle size={16} />}>
          Prenotazioni non disponibili
        </Alert>
      ) : (
        <Tabs
          value={activeTab}
          onChange={(v) => setActiveTab((v as Mode) || 'reserve')}
        >
          <Tabs.List grow>
            <Tabs.Tab value="reserve" leftSection={<IconCalendar size={16} />}>
              Prenota online
            </Tabs.Tab>
            <Tabs.Tab value="walkin" leftSection={<IconWalk size={16} />}>
              Sono al parco
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="reserve" pt="md">
            <Paper withBorder p="xl" radius="md">
              <Text ta="center" mb="lg" fw={500}>
                Prenota il tuo posto GRATIS
              </Text>
              <form onSubmit={reserveForm.onSubmit((v) =>
                reserveMutation.mutate({
                  first_name: v.first_name.trim(),
                  last_name: v.last_name.trim(),
                  email: v.email || undefined,
                  newsletter_opt_in: v.newsletter,
                })
              )}>
                <Stack>
                  <TextInput
                    label="Nome"
                    placeholder="Mario"
                    required
                    leftSection={<IconUser size={16} />}
                    {...reserveForm.getInputProps('first_name')}
                  />
                  <TextInput
                    label="Cognome"
                    placeholder="Rossi"
                    required
                    leftSection={<IconUser size={16} />}
                    {...reserveForm.getInputProps('last_name')}
                  />
                  <TextInput
                    label="Email (opzionale)"
                    placeholder="mario@email.it"
                    leftSection={<IconMail size={16} />}
                    {...reserveForm.getInputProps('email')}
                  />
                  <Checkbox
                    label="Tienimi aggiornato su prossimi eventi"
                    {...reserveForm.getInputProps('newsletter', { type: 'checkbox' })}
                  />
                  <Button
                    type="submit"
                    size="lg"
                    fullWidth
                    loading={reserveMutation.isPending}
                  >
                    🎫 Prenota ora
                  </Button>
                  <Text size="xs" c="dimmed" ta="center">
                    Riceverai il QR sullo schermo. Fai uno screenshot per il giorno dell'evento.
                  </Text>
                </Stack>
              </form>
            </Paper>
          </Tabs.Panel>

          <Tabs.Panel value="walkin" pt="md">
            <Paper withBorder p="xl" radius="md">
              <Text ta="center" mb="xs" fw={500}>
                Check-in diretto
              </Text>
              <Text size="sm" c="dimmed" ta="center" mb="lg">
                Il sistema ti assegna subito un posto. Mostra il QR all'operatore.
              </Text>
              <form onSubmit={walkinForm.onSubmit((v) =>
                walkinMutation.mutate({
                  first_name: v.first_name.trim(),
                  last_name: v.last_name.trim(),
                })
              )}>
                <Stack>
                  <TextInput
                    label="Nome"
                    placeholder="Mario"
                    required
                    leftSection={<IconUser size={16} />}
                    {...walkinForm.getInputProps('first_name')}
                  />
                  <TextInput
                    label="Cognome"
                    placeholder="Rossi"
                    required
                    leftSection={<IconUser size={16} />}
                    {...walkinForm.getInputProps('last_name')}
                  />
                  <Button
                    type="submit"
                    size="lg"
                    fullWidth
                    color="teal"
                    loading={walkinMutation.isPending}
                  >
                    🚲 Assegnami un posto
                  </Button>
                  <Divider my="xs" />
                  <Text size="xs" c="dimmed" ta="center">
                    Senza smartphone? Chiedi all'operatore di gestirti con un gettone fisico.
                  </Text>
                </Stack>
              </form>
            </Paper>
          </Tabs.Panel>
        </Tabs>
      )}

      <Text c="dimmed" size="xs" ta="center" mt="xl">
        by Scintilla Cicloprogetti
      </Text>
    </Container>
  );
}
