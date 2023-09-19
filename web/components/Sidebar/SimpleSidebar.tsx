import { ReactNode } from 'react';

import {
  CloseSidebarButton,
  OpenSidebarButton,
} from './components/OpenCloseButton';

interface Props<T> {
  isOpen: boolean;
  side: 'left' | 'right';
  component: ReactNode;
  toggleOpen: () => void;
}

const SimpleSidebar = <T,>({
  isOpen,
  toggleOpen,
  side,
  component,
}: Props<T>) => {
  const allowDrop = (e: any) => {
    e.preventDefault();
  };

  return isOpen ? (
    <div>
      <div
        className={`fixed top-0 ${side}-0 z-40 flex h-full w-[260px] flex-none flex-col space-y-2 bg-[#202123] p-2 text-[14px] transition-all sm:relative sm:top-0`}
      >
        <div className="flex items-center"></div>

        {component}
      </div>

      <CloseSidebarButton onClick={toggleOpen} side={side} />
    </div>
  ) : (
    <OpenSidebarButton onClick={toggleOpen} side={side} />
  );
};

export default SimpleSidebar;
