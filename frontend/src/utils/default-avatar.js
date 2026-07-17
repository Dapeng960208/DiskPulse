import avatarLilac from '@/assets/images/default-avatars/default-avatar-lilac.gif';
import avatarMint from '@/assets/images/default-avatars/default-avatar-mint.gif';
import avatarPeach from '@/assets/images/default-avatars/default-avatar-peach.gif';
import avatarSky from '@/assets/images/default-avatars/default-avatar-sky.gif';

const DEFAULT_AVATARS = [avatarMint, avatarPeach, avatarSky, avatarLilac];

function stableHash(value) {
  return [...String(value)].reduce((hash, character) => ((hash * 31) + character.charCodeAt(0)) >>> 0, 0);
}

export function getDefaultAvatar(userIdentity) {
  return DEFAULT_AVATARS[stableHash(userIdentity) % DEFAULT_AVATARS.length];
}
